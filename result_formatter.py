from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message
import json


class ResultFormatter(Component):
    display_name = "Result Formatter"
    description = "Formats ScamShield JSON output into professional, readable text"
    
    inputs = [
        MessageTextInput(
            name="json_input",
            display_name="JSON Input",
            info="Raw JSON output from Score Combiner"
        )
    ]
    
    outputs = [
        Output(display_name="Formatted Output", name="output", method="format_result")
    ]
    
    def format_result(self) -> Message:
        try:
            # Parse JSON input
            data = json.loads(self.json_input)
            
            # Extract data
            score = round(data.get('final_score', 0))
            verdict = data.get('final_verdict', 'UNKNOWN')
            color = data.get('color', 'green')
            risk_level = data.get('risk_level', 'Unknown Risk')
            explanation = data.get('explain_brief', 'No explanation provided')
            
            # Score breakdown
            breakdown = data.get('breakdown', {})
            heuristic = breakdown.get('heuristic', 0)
            domain = breakdown.get('domain', 0)
            llm = breakdown.get('llm', 0)
            
            # Flags and recommendations
            heuristic_flags = data.get('heuristic_flags', [])
            top_reasons = data.get('top_reasons', [])
            next_steps = data.get('next_steps', [])
            
            # Combine unique flags
            all_flags = list(set(heuristic_flags + top_reasons))
            
            # Status indicators
            status_icon = {
                'green': '✓',
                'yellow': '⚠',
                'red': '✕'
            }.get(color, '•')
            
            # Progress bar
            bar_length = 20
            filled = int((score / 100) * bar_length)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            # ═══════════════════════════════════════════
            # BUILD OUTPUT - FORCE LINE BREAKS
            # ═══════════════════════════════════════════
            
            output = "**SCAMSHIELD ANALYSIS REPORT**"
            output += "\n\n"
            
            output += f"**Status:** {status_icon} {verdict.upper()}"
            output += "\n\n"
            
            output += f"**Risk Level:** {risk_level}"
            output += "\n\n"
            
            output += f"**Risk Score:** {score}/100"
            output += "\n\n"
            
            output += f"[{bar}]"
            output += "\n\n"

            # Confidence (if available)
            if 'confidence' in data:
                confidence = data['confidence']
                output += f"**Analysis Confidence:** {confidence}"
                output += "\n\n"

            output += "─" * 50
            output += "\n\n"
            
            # Assessment
            output += "**ASSESSMENT**"
            output += "\n\n"
            
            output += f"{explanation}"
            output += "\n\n"
            
            output += "─" * 50
            output += "\n\n"
            
            # Key Findings
            output += "**KEY FINDINGS**"
            output += "\n\n"
            
            if all_flags:
                for i, flag in enumerate(all_flags[:6], 1):
                    clean_flag = flag.replace('🚨', '').replace('⚠️', '').replace('✅', '').strip()
                    output += f"{i}. {clean_flag}"
                    output += "\n"
                output += "\n"
            else:
                output += "No significant risk indicators detected."
                output += "\n\n"
            
            output += "─" * 50
            output += "\n\n"
            
            # Recommendations
            output += "**RECOMMENDATIONS**"
            output += "\n\n"
            
            if next_steps:
                for i, step in enumerate(next_steps[:4], 1):
                    clean_step = step.replace('✅', '').replace('⚠️', '').replace('🚨', '').strip()
                    output += f"{i}. {clean_step}"
                    output += "\n"
                output += "\n"
            else:
                output += "Proceed with standard verification."
                output += "\n\n"
            
            output += "─" * 50
            output += "\n\n"
            
            # Analysis Breakdown
            output += "**ANALYSIS BREAKDOWN**"
            output += "\n\n"
            
            output += f"**Pattern Recognition:** {heuristic}/100"
            output += "\n\n"
            
            output += f"**Domain Validation:** {domain}/100"
            output += "\n\n"
            
            output += f"**AI Contextual Analysis:** {llm}/100"
            output += "\n\n"

            # Weights (if available)
            if 'weights_used' in data:
                weights = data['weights_used']
                output += "**Weighting Applied:**"
                output += "\n\n"
                
                output += f"• Pattern: {int(weights['h']*100)}%"
                output += "\n\n"
                
                output += f"• Domain: {int(weights['d']*100)}%"
                output += "\n\n"
                
                output += f"• AI: {int(weights['l']*100)}%"
                output += "\n\n"

            output += "─" * 50
            output += "\n\n"
            
            output += "Note: Analysis is ephemeral. No data is stored or tracked."
            
            return Message(text=output.strip())
            
        except json.JSONDecodeError:
            return Message(text="ERROR: Invalid data format. Please try again.")
        
        except Exception as e:
            return Message(text=f"ERROR: Analysis failed. {str(e)}")
