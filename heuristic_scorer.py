from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message
import re
import json


class AdvancedHeuristicScorer(Component):
    display_name = "Advanced Heuristic Scorer"
    description = "Enhanced pattern detection with 50+ scam indicators"
    
    inputs = [
        MessageTextInput(
            name="text_input",
            display_name="Text to Analyze",
            info="Job posting text"
        )
    ]
    
    outputs = [
        Output(display_name="Heuristic Result", name="output", method="analyze")
    ]
    
    def analyze(self) -> Message:
        text = self.text_input.lower()
        score = 0
        flags = []
        
    
        critical_patterns = {
            'registration fee': 35,
            'processing fee': 35,
            'security deposit': 35,
            'pay for training': 35,
            'investment required': 40,
            'send money': 40,
            'western union': 45,
            'gift card': 45,
            'bitcoin': 40,
            'cryptocurrency': 40
        }
        
        for pattern, points in critical_patterns.items():
            if pattern in text:
                score += points
                flags.append(f"🚨 CRITICAL: '{pattern}' detected")
        
    
        high_risk = {
            'urgent hiring': 25,
            'limited slots': 25,
            'act fast': 25,
            'immediate joining': 25,
            'first come first serve': 25,
            'telegram': 20,
            'whatsapp only': 25,
            'no experience needed': 15,
            'work from home': 10,
            'earn daily': 25,
            'guaranteed income': 30,
            'easy money': 30
        }
        
        for pattern, points in high_risk.items():
            if pattern in text:
                score += points
                flags.append(f"⚠️ High Risk: '{pattern}'")
        
        # ═══════════════════════════════════════════
        # SALARY REALITY CHECK (NEW!)
        # ═══════════════════════════════════════════
        
        # Daily salary check
        daily_salary = re.findall(r'₹?\s*(\d+(?:,\d+)*)\s*(?:daily|per day|/day)', text)
        for match in daily_salary:
            amount = int(match.replace(',', ''))
            if amount > 3000:  # ₹3k+ daily = ₹90k+ monthly
                score += 30
                flags.append(f"💰 Unrealistic daily salary: ₹{amount:,}/day")
            elif amount > 5000:
                score += 40
                flags.append(f"🚨 EXTREME: ₹{amount:,}/day (impossible)")
        
        # Monthly/Annual salary check
        monthly_salary = re.findall(r'₹?\s*(\d+(?:,\d+)*)\s*(?:lpa|per annum|/year)', text)
        for match in monthly_salary:
            amount = int(match.replace(',', ''))
            if amount > 5000000:  # 50L+ for entry-level
                score += 25
                flags.append(f"⚠️ Extremely high salary: ₹{amount:,} LPA")
        
        # ═══════════════════════════════════════════
        # PHONE NUMBER PATTERNS (NEW!)
        # ═══════════════════════════════════════════
        phone_pattern = r'(?:\+91|0)?[6-9]\d{9}'
        phones = re.findall(phone_pattern, text)
        
        if len(phones) > 2:
            score += 20
            flags.append(f"📱 Multiple phone numbers ({len(phones)})")
        
        # Check for international numbers (scam indicator)
        intl_phones = re.findall(r'\+(?!91)\d{1,3}\d{7,}', text)
        if intl_phones:
            score += 30
            flags.append(f"🌍 International phone number detected")
        
        # ═══════════════════════════════════════════
        # EMAIL PATTERNS (NEW!)
        # ═══════════════════════════════════════════
        emails = re.findall(r'[\w\.-]+@([\w\.-]+)', text)
        
        suspicious_emails = ['gmail.com', 'yahoo.com', 'hotmail.com', 
                            'outlook.com', 'rediffmail.com']
        
        for domain in emails:
            if domain.lower() in suspicious_emails:
                score += 15
                flags.append(f"📧 Generic email domain: {domain}")
        
        # ═══════════════════════════════════════════
        # GRAMMAR & SPELLING ISSUES (NEW!)
        # ═══════════════════════════════════════════
        grammar_issues = [
            'cant', 'wont', 'dont',  # Missing apostrophes
            'pls', 'plz', 'msg',     # Abbreviations
            'dm me', 'inbox me'       # Unprofessional
        ]
        
        grammar_count = sum(1 for issue in grammar_issues if issue in text)
        if grammar_count >= 2:
            score += 15
            flags.append(f"✍️ Poor grammar/spelling ({grammar_count} issues)")
        
        # ═══════════════════════════════════════════
        # MISSING CRITICAL INFO (NEW!)
        # ═══════════════════════════════════════════
        required_fields = {
            'company name': ['company:', 'organization:', 'employer:'],
            'job title': ['position:', 'role:', 'job title:'],
            'location': ['location:', 'city:', 'office:'],
            'qualifications': ['qualification', 'education', 'degree']
        }
        
        missing_count = 0
        for field, keywords in required_fields.items():
            if not any(keyword in text for keyword in keywords):
                missing_count += 1
        
        if missing_count >= 3:
            score += 20
            flags.append(f"📋 Missing {missing_count} critical details")
        
        # ═══════════════════════════════════════════
        # EMOTIONAL MANIPULATION (NEW!)
        # ═══════════════════════════════════════════
        manipulation_words = [
            'amazing opportunity', 'once in lifetime', 
            'exclusive offer', 'secret method',
            'financial freedom', 'be your own boss',
            'passive income', 'get rich'
        ]
        
        manipulation_count = sum(1 for word in manipulation_words if word in text)
        if manipulation_count >= 2:
            score += 20
            flags.append(f"🎭 Emotional manipulation tactics detected")
        
        # ═══════════════════════════════════════════
        # CAPS LOCK ABUSE (NEW!)
        # ═══════════════════════════════════════════
        caps_words = [word for word in text.split() if word.isupper() and len(word) > 3]
        if len(caps_words) > 5:
            score += 15
            flags.append(f"📢 Excessive CAPS ({len(caps_words)} words)")
        
        # ═══════════════════════════════════════════
        # FINAL SCORE CAPPING
        # ═══════════════════════════════════════════
        score = min(score, 100)
        
        result = {
            'heuristic_score': score,
            'heuristic_flags': flags[:10]  # Limit to 10 flags
        }
        
        return Message(text=json.dumps(result))
