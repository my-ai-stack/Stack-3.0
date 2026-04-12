"""
Conversation quality evaluation for Stack 3.0
Measures context retention, multi-turn coherence, error recovery, and user satisfaction
"""

import json
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import random

class ConversationQualityEvaluator:
    def __init__(self, conversation_history_path: str = "conversations.json"):
        self.conversation_history_path = conversation_history_path
        self.conversations = self._load_conversations()
        self.results = {}
    
    def _load_conversations(self) -> List[Dict]:
        """Load conversation history"""
        try:
            with open(self.conversation_history_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Conversation history not found at {self.conversation_history_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error parsing conversation history")
            return []
    
    def evaluate_conversations(self) -> Dict[str, Any]:
        """Evaluate all conversations"""
        print("Evaluating conversation quality...")
        
        if not self.conversations:
            print("No conversations found for evaluation")
            return {}
        
        total_conversations = len(self.conversations)
        print(f"Evaluating {total_conversations} conversations")
        
        context_retention_scores = []
        coherence_scores = []
        error_recovery_scores = []
        satisfaction_scores = []
        
        for i, conversation in enumerate(self.conversations):
            print(f"Evaluating conversation {i+1}/{total_conversations}...")
            
            scores = self._evaluate_single_conversation(conversation)
            
            context_retention_scores.append(scores["context_retention"])
            coherence_scores.append(scores["coherence"])
            error_recovery_scores.append(scores["error_recovery"])
            satisfaction_scores.append(scores["satisfaction"])
        
        return {
            "summary": {
                "total_conversations": total_conversations,
                "average_context_retention": self._calculate_average(context_retention_scores),
                "average_coherence": self._calculate_average(coherence_scores),
                "average_error_recovery": self._calculate_average(error_recovery_scores),
                "average_satisfaction": self._calculate_average(satisfaction_scores)
            },
            "detailed_results": self.results
        }
    
    def _evaluate_single_conversation(self, conversation: Dict) -> Dict[str, float]:
        """Evaluate a single conversation"""
        conversation_id = conversation.get("id", str(random.randint(1000, 9999)))
        
        # Measure context retention
        context_retention = self._measure_context_retention(conversation)
        
        # Measure multi-turn coherence
        coherence = self._measure_coherence(conversation)
        
        # Measure error recovery
        error_recovery = self._measure_error_recovery(conversation)
        
        # Measure user satisfaction (proxy metrics)
        satisfaction = self._measure_satisfaction(conversation)
        
        self.results[conversation_id] = {
            "context_retention": context_retention,
            "coherence": coherence,
            "error_recovery": error_recovery,
            "satisfaction": satisfaction,
            "message_count": len(conversation.get("messages", [])),
            "duration_minutes": self._calculate_conversation_duration(conversation)
        }
        
        return {
            "context_retention": context_retention,
            "coherence": coherence,
            "error_recovery": error_recovery,
            "satisfaction": satisfaction
        }
    
    def _measure_context_retention(self, conversation: Dict) -> float:
        """Measure how well the model retains context"""
        messages = conversation.get("messages", [])
        
        if len(messages) < 3:
            return 1.0  # Not enough context to evaluate
        
        # Check if later messages reference earlier context
        retention_score = 0
        reference_count = 0
        
        # Look for references to earlier messages
        for i in range(len(messages) - 1, 1, -1):
            current_message = messages[i]
            earlier_messages = messages[:i]
            
            # Check if current message references earlier context
            if self._contains_reference(current_message, earlier_messages):
                retention_score += 1
                reference_count += 1
        
        return retention_score / (len(messages) - 2) if len(messages) > 2 else 1.0
    
    def _contains_reference(self, message: Dict, earlier_messages: List[Dict]) -> bool:
        """Check if message contains reference to earlier messages"""
        content = message.get("content", "").lower()
        
        # Check for explicit references
        if "as mentioned" in content or "earlier" in content or "before" in content:
            return True
        
        # Check for topic continuity
        for earlier in earlier_messages[-3:]:  # Check last 3 messages
            earlier_content = earlier.get("content", "").lower()
            if any(keyword in content for keyword in [earlier_content[:20], earlier_content.split()[0]]):
                return True
        
        return False
    
    def _measure_coherence(self, conversation: Dict) -> float:
        """Measure multi-turn coherence"""
        messages = conversation.get("messages", [])
        
        if len(messages) < 2:
            return 1.0
        
        coherence_breaks = 0
        
        for i in range(1, len(messages)):
            prev_message = messages[i-1]
            current_message = messages[i]
            
            # Check if current message is on-topic with previous
            if not self._is_coherent(prev_message, current_message):
                coherence_breaks += 1
        
        return 1.0 - (coherence_breaks / (len(messages) - 1)) if len(messages) > 1 else 1.0
    
    def _is_coherent(self, message1: Dict, message2: Dict) -> bool:
        """Check if two messages are coherent"""
        content1 = message1.get("content", "").lower()
        content2 = message2.get("content", "").lower()
        
        # Check for topic similarity
        common_words = set(content1.split()) & set(content2.split())
        
        # If they share at least one significant word, consider coherent
        significant_words = {w for w in common_words if len(w) > 3}
        
        return len(significant_words) > 0
    
    def _measure_error_recovery(self, conversation: Dict) -> float:
        """Measure error recovery capability"""
        messages = conversation.get("messages", [])
        
        if len(messages) < 3:
            return 1.0
        
        error_recovery_count = 0
        
        # Look for error patterns and recovery
        for i in range(1, len(messages)):
            prev_message = messages[i-1]
            current_message = messages[i]
            
            # Check if current message corrects or recovers from previous error
            if self._is_error_recovery(prev_message, current_message):
                error_recovery_count += 1
        
        return error_recovery_count / (len(messages) - 1) if len(messages) > 1 else 1.0
    
    def _is_error_recovery(self, message1: Dict, message2: Dict) -> bool:
        """Check if message2 recovers from error in message1"""
        content1 = message1.get("content", "").lower()
        content2 = message2.get("content", "").lower()
        
        # Check for correction patterns
        corrections = [
            "correction:", "actually", "sorry", "correction", "correction to",
            "i meant", "meant to say", "correction -", "correction--"
        ]
        
        return any(correction in content2 for correction in corrections)
    
    def _measure_satisfaction(self, conversation: Dict) -> float:
        """Measure user satisfaction (proxy metrics)"""
        messages = conversation.get("messages", [])
        
        if not messages:
            return 0.0
        
        # Check for positive sentiment in user messages
        positive_indicators = 0
        
        for message in messages:
            if message.get("role") == "user":
                content = message.get("content", "").lower()
                
                positive_words = [
                    "thanks", "thank you", "great", "good", "excellent", 
                    "perfect", "awesome", "wonderful", "love", "amazing"
                ]
                
                if any(word in content for word in positive_words):
                    positive_indicators += 1
        
        # Check conversation length (longer conversations often indicate satisfaction)
        conversation_length = len(messages)
        
        # Combine metrics
        satisfaction_score = (positive_indicators / len(messages)) * 0.5 + \
                           (min(conversation_length, 20) / 20) * 0.5
        
        return satisfaction_score
    
    def _calculate_conversation_duration(self, conversation: Dict) -> float:
        """Calculate conversation duration in minutes"""
        messages = conversation.get("messages", [])
        
        if len(messages) < 2:
            return 0.0
        
        try:
            start_time = datetime.fromisoformat(messages[0]["timestamp"].replace("Z", ""))
            end_time = datetime.fromisoformat(messages[-1]["timestamp"].replace("Z", ""))
            duration = end_time - start_time
            return duration.total_seconds() / 60.0
        except:
            return 0.0
    
    def _calculate_average(self, scores: List[float]) -> float:
        """Calculate average of scores"""
        return sum(scores) / len(scores) if scores else 0.0
    
    def generate_report(self) -> str:
        """Generate markdown report"""
        results = self.evaluate_conversations()
        summary = results.get("summary", {})
        
        report = f"""# Conversation Quality Evaluation Report

## Summary
Evaluation of conversation quality for Stack 3.0.

## Overall Statistics

| Metric | Value |
|--------|-------|
| Total Conversations | {summary[\"total_conversations\"]} |
| Average Context Retention | {summary[\"average_context_retention\"]:.2%} |
| Average Coherence | {summary[\"average_coherence\"]:.2%} |
| Average Error Recovery | {summary[\"average_error_recovery\"]:.2%} |
| Average Satisfaction | {summary[\"average_satisfaction\"]:.2%} |

## Conversation Details

"""
        
        for conv_id, result in self.results.items():
            report += f"""### Conversation {conv_id}

- **Messages**: {result[\"message_count\"]}
- **Duration**: {result[\"duration_minutes\"]:.1f} minutes
- **Context Retention**: {result[\"context_retention\"]:.2%}
- **Coherence**: {result[\"coherence\"]:.2%}
- **Error Recovery**: {result[\"error_recovery\"]:.2%}
- **Satisfaction**: {result[\"satisfaction\"]:.2%}

"""
        
        return report


if __name__ == "__main__":
    evaluator = ConversationQualityEvaluator()
    results = evaluator.evaluate_conversations()
    
    print("Conversation Quality Evaluation Complete!")
    print(json.dumps(results, indent=2))
    
    report = evaluator.generate_report()
    print(report)
    
    # Save results
    with open("results/conversation_quality_evaluation.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    with open("results/conversation_quality_report.md", 'w') as f:
        f.write(report)