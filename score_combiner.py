from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema.message import Message
import json


class SmartScoreCombiner(Component):
    display_name = "Score Combiner"
    description = "Dynamic weighted scoring based on confidence"
    
    inputs = [
        MessageTextInput(name="heuristic_result", display_name="Heuristic Result"),
        MessageTextInput(name="domain_result", display_name="Domain Result"),
        MessageTextInput(name="llm_result", display_name="LLM Result")
    ]
    
    outputs = [
        Output(display_name="Final Result", name="output", method="combine")
    ]
    
    def combine(self) -> Message:
        # Parse inputs
        heuristic = json.loads(self.heuristic_result)
        domain = json.loads(self.domain_result)
        llm = json.loads(self.llm_result)
        
        h_score = heuristic.get('heuristic_score', 0)
        d_score = domain.get('domain_score', 0)
        l_score = llm.get('llm_score', 0)
        
        # ═══════════════════════════════════════════
        # DYNAMIC WEIGHTING (NEW!)
        # ═══════════════════════════════════════════
        
        # If heuristic finds critical flags, trust it more
        critical_flags = len([f for f in heuristic.get('heuristic_flags', []) 
                             if '🚨' in f])
        
        if critical_flags >= 2:
            # Obvious scam - trust heuristics more
            weights = {'h': 0.50, 'd': 0.25, 'l': 0.25}
        elif d_score > 70:
            # Domain issues - trust domain check more
            weights = {'h': 0.25, 'd': 0.50, 'l': 0.25}
        else:
            # Normal case - trust LLM more
            weights = {'h': 0.30, 'd': 0.30, 'l': 0.40}
        
        final_score = (
            h_score * weights['h'] +
            d_score * weights['d'] +
            l_score * weights['l']
        )
        
        final_score = round(final_score)
        
        # ═══════════════════════════════════════════
        # SMART VERDICT (NEW!)
        # ═══════════════════════════════════════════
        
        # If all three agree (within 20 points), high confidence
        scores = [h_score, d_score, l_score]
        score_range = max(scores) - min(scores)
        
        if score_range < 20:
            confidence = "High"
        elif score_range < 40:
            confidence = "Medium"
        else:
            confidence = "Low"
        
        # Determine verdict
        if final_score <= 25:
            verdict = "SAFE"
            risk_level = "Low Risk"
            color = "green"
        elif final_score <= 60:
            verdict = "SUSPICIOUS"
            risk_level = "Medium Risk"
            color = "yellow"
        else:
            verdict = "SCAM"
            risk_level = "High Risk"
            color = "red"
        
        # ═══════════════════════════════════════════
        # SMART RECOMMENDATIONS (NEW!)
        # ═══════════════════════════════════════════
        
        if final_score <= 25:
            next_steps = [
                "✅ Verify company on official website",
                "✅ Read employee reviews on Glassdoor",
                "✅ Check if job is on company's career page",
                "✅ Proceed with standard application"
            ]
        elif final_score <= 60:
            next_steps = [
                "⚠️ DO NOT share personal documents yet",
                "⚠️ Verify company registration (MCA database)",
                "⚠️ Request interview on official platform",
                "⚠️ Ask for official company email",
                "⚠️ Check company address on Google Maps"
            ]
        else:
            next_steps = [
                "🚨 DO NOT ENGAGE with this posting",
                "🚨 DO NOT send money or documents",
                "🚨 Report to cybercrime.gov.in",
                "🚨 Block contact immediately",
                "🚨 Warn others in your network"
            ]
        
        # Combine all flags
        all_flags = (
            heuristic.get('heuristic_flags', []) +
            domain.get('domain_flags', []) +
            llm.get('top_reasons', [])
        )
        
        result = {
            'final_score': final_score,
            'final_verdict': verdict,
            'risk_level': risk_level,
            'color': color,
            'confidence': confidence,  # NEW!
            'breakdown': {
                'heuristic': h_score,
                'domain': d_score,
                'llm': l_score
            },
            'weights_used': weights,  # NEW!
            'heuristic_flags': heuristic.get('heuristic_flags', []),
            'domain_flags': domain.get('domain_flags', []),
            'top_reasons': llm.get('top_reasons', []),
            'explain_brief': llm.get('explain_brief', ''),
            'next_steps': next_steps,
            'all_flags': list(set(all_flags))[:8]  # Top 8 unique flags
        }
        
        return Message(text=json.dumps(result))
