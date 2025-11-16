from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message
import re
import json
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup


class EnhancedDomainValidator(Component):
    display_name = "Enhanced Domain Validator"
    description = "Validates domains by actually visiting URLs and reading job descriptions"
    
    inputs = [
        MessageTextInput(
            name="text_input",
            display_name="Text to Analyze",
            info="Job posting text with URLs"
        )
    ]
    
    outputs = [
        Output(display_name="Domain Result", name="output", method="validate_domains")
    ]
    
    def validate_domains(self) -> Message:
        try:
            text = self.text_input
            score = 0
            flags = []
            
            # ═══════════════════════════════════════════
            # TRUSTED PLATFORMS (Baseline Check)
            # ═══════════════════════════════════════════
            trusted_domains = [
                'linkedin.com', 'naukri.com', 'indeed.com', 
                'internshala.com', 'shine.com', 'monster.com',
                'glassdoor.com', 'foundit.in', 'apna.co',
                'hirist.com', 'freshersworld.com'
            ]
            
            # ═══════════════════════════════════════════
            # EXTRACT URLs FROM TEXT
            # ═══════════════════════════════════════════
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            urls = re.findall(url_pattern, text)
            
            # Also check for domains mentioned without http
            domain_pattern = r'(?:www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?)'
            mentioned_domains = re.findall(domain_pattern, text)
            
            # ═══════════════════════════════════════════
            # EXTRACT EMAIL DOMAINS
            # ═══════════════════════════════════════════
            emails = re.findall(r'[\w\.-]+@([\w\.-]+)', text)
            
            # ═══════════════════════════════════════════
            # CHECK EMAIL DOMAINS
            # ═══════════════════════════════════════════
            for email_domain in emails:
                if email_domain.lower() in ['gmail.com', 'yahoo.com', 'hotmail.com', 
                                              'outlook.com', 'rediffmail.com']:
                    score += 20
                    flags.append(f"🚩 Generic email provider: {email_domain}")
                else:
                    # Corporate email - good sign
                    score -= 10
                    flags.append(f"✅ Corporate email domain: {email_domain}")
            
            # ═══════════════════════════════════════════
            # PROCESS EACH URL (ACTUAL BROWSING)
            # ═══════════════════════════════════════════
            if urls:
                for url in urls[:3]:  # Limit to 3 URLs to avoid timeout
                    url_score, url_flags = self.check_url(url, trusted_domains)
                    score += url_score
                    flags.extend(url_flags)
            else:
                # No URLs found - suspicious for job postings
                if any(keyword in text.lower() for keyword in ['apply', 'job', 'hiring', 'position']):
                    score += 25
                    flags.append("🚩 No official URL provided for application")
            
            # ═══════════════════════════════════════════
            # CHECK FOR MESSAGING APP RECRUITMENT
            # ═══════════════════════════════════════════
            if 'whatsapp' in text.lower() or 'telegram' in text.lower():
                has_legitimate_url = any(
                    any(trusted in url.lower() for trusted in trusted_domains) 
                    for url in urls
                )
                if not has_legitimate_url:
                    score += 30
                    flags.append("🚨 Recruitment via messaging apps (WhatsApp/Telegram)")
            
            # ═══════════════════════════════════════════
            # CAP SCORE BETWEEN 0-100
            # ═══════════════════════════════════════════
            score = max(0, min(score, 100))
            
            # ═══════════════════════════════════════════
            # BUILD RESULT JSON
            # ═══════════════════════════════════════════
            result = {
                'domain_score': score,
                'domain_flags': flags
            }
            
            return Message(text=json.dumps(result))
            
        except Exception as e:
            error_result = {
                'domain_score': 50,
                'domain_flags': [f"⚠️ Error in domain validation: {str(e)}"]
            }
            return Message(text=json.dumps(error_result))
    
    # ═══════════════════════════════════════════
    # URL CHECKING FUNCTION (THE MAGIC PART)
    # ═══════════════════════════════════════════
    def check_url(self, url: str, trusted_domains: list) -> tuple:
        """
        Actually visits the URL and analyzes the page
        Returns: (score_adjustment, flags_list)
        """
        score = 0
        flags = []
        
        try:
            # Set timeout to avoid hanging
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
            
            # ═══════════════════════════════════════════
            # CHECK 1: HTTP Status Code
            # ═══════════════════════════════════════════
            if response.status_code == 200:
                flags.append(f"✅ URL is accessible: {urlparse(url).netloc}")
            elif response.status_code == 404:
                score += 40
                flags.append(f"🚨 URL not found (404): {url}")
                return (score, flags)
            else:
                score += 20
                flags.append(f"⚠️ URL returned status {response.status_code}")
            
            # ═══════════════════════════════════════════
            # CHECK 2: HTTPS (Secure Connection)
            # ═══════════════════════════════════════════
            if url.startswith('https://'):
                score -= 5
                flags.append("✅ Uses secure HTTPS")
            else:
                score += 15
                flags.append("🚩 No HTTPS encryption")
            
            # ═══════════════════════════════════════════
            # CHECK 3: Trusted Platform
            # ═══════════════════════════════════════════
            domain = urlparse(url).netloc.lower()
            is_trusted = any(trusted in domain for trusted in trusted_domains)
            
            if is_trusted:
                score -= 30
                flags.append(f"✅ Posted on trusted platform: {domain}")
            else:
                score += 15
                flags.append(f"⚠️ Unknown platform: {domain}")
            
            # ═══════════════════════════════════════════
            # CHECK 4: Parse HTML Content
            # ═══════════════════════════════════════════
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for job-related meta tags
            og_type = soup.find('meta', property='og:type')
            if og_type and 'job' in og_type.get('content', '').lower():
                score -= 15
                flags.append("✅ Confirmed job posting page")
            
            # Check for job schema markup
            job_schema = soup.find('script', type='application/ld+json')
            if job_schema and 'JobPosting' in job_schema.string:
                score -= 10
                flags.append("✅ Contains structured job data")
            
            # ═══════════════════════════════════════════
            # CHECK 5: Content Analysis
            # ═══════════════════════════════════════════
            page_text = soup.get_text().lower()
            
            # Look for job-related keywords
            job_keywords = ['salary', 'requirements', 'qualifications', 
                           'experience', 'apply now', 'job description']
            keyword_count = sum(1 for keyword in job_keywords if keyword in page_text)
            
            if keyword_count >= 4:
                score -= 10
                flags.append(f"✅ Page contains job details ({keyword_count}/6 keywords)")
            elif keyword_count < 2:
                score += 10
                flags.append("⚠️ Page lacks proper job description")
            
            # Check for scam indicators on page
            scam_indicators = ['registration fee', 'processing fee', 'security deposit',
                              'immediate joining', 'urgent hiring', 'limited slots']
            scam_count = sum(1 for indicator in scam_indicators if indicator in page_text)
            
            if scam_count >= 2:
                score += 20
                flags.append(f"🚨 Page contains {scam_count} scam indicators")
            
            # ═══════════════════════════════════════════
            # CHECK 6: Redirects (Suspicious)
            # ═══════════════════════════════════════════
            if len(response.history) > 2:
                score += 15
                flags.append(f"⚠️ Multiple redirects detected ({len(response.history)})")
            
            return (score, flags)
            
        except requests.exceptions.Timeout:
            return (25, [f"⚠️ URL timed out (slow/suspicious): {url}"])
        
        except requests.exceptions.SSLError:
            return (30, [f"🚨 SSL certificate error: {url}"])
        
        except requests.exceptions.ConnectionError:
            return (35, [f"🚨 Could not connect to URL: {url}"])
        
        except Exception as e:
            return (20, [f"⚠️ Error checking URL: {str(e)[:50]}"])
