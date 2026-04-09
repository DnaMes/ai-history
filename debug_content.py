import sys
from pathlib import Path

# Add local package
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ai_history.extractors.factory import get_all_extractors

def debug_latest():
    print("🔍 Scanning for latest session with Tool Results...")
    extractors = get_all_extractors()
    
    for ex in extractors:
        if not ex.is_available(): continue
        
        # Get latest session
        try:
            sessions = list(ex.extract_sessions())
            if not sessions: continue
            # Sort by date
            sessions.sort(key=lambda s: s.created_at, reverse=True)
            
            for s in sessions[:5]:
                for msg in s.messages:
                    if "[Tool Result]" in msg.content:
                        print(f"\nFOUND in Session {s.session_id} ({ex.tool.value}):")
                        print("-" * 40)
                        # Print raw content snippet around tool result
                        start = msg.content.find("[Tool Result]")
                        end = start + 500
                        print(msg.content[start:end])
                        print("-" * 40)
                        print("REPR:")
                        print(repr(msg.content[start:end]))
                        return
        except Exception as e:
            print(e)

if __name__ == "__main__":
    debug_latest()

