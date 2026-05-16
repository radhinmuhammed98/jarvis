import re

def normalize_speech_text(text: str) -> str:
    """Normalize Indian/Manglish slang and fix common STT mistakes."""
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Strip punctuation
    text = re.sub(r'[^\w\s]', '', text).strip()
    
    # Define exact phrase replacements
    # Using a dictionary for exact matches first, then partial replacements if needed.
    # Order matters for some of these if doing partial replacement, but exact match is safer.
    
    # Let's do exact mapping first for whole-phrase commands
    exact_mappings = {
        # Greetings
        "hii": "hey",
        "hiii": "hey",
        "heyy": "hey",
        "hyy": "hey",
        "oi": "hey",
        "oioi": "hey",
        
        # Light ON
        "velicham kathikkoo": "turn on light",
        "velicham kathik": "turn on light",
        "light kathikkoo": "turn on light",
        "kathikkoo": "turn on light",
        "kathik": "turn on light",
        "on akku light": "turn on light",
        "light on cheyy": "turn on light",
        "light on akku": "turn on light",
        "switch on light": "turn on light",
        "turn on lite": "turn on light",
        "turn on life": "turn on light",
        "turn on right": "turn on light",
        
        # Light OFF
        "velicham keduthu": "turn off light",
        "velicham keduth": "turn off light",
        "light keduthu": "turn off light",
        "keduthu": "turn off light",
        "keduth": "turn off light",
        "off akku light": "turn off light",
        "light off cheyy": "turn off light",
        "light off akku": "turn off light",
        "turn of light": "turn off light",
        
        # Common Jarvis command corrections
        "open inter net": "open internet",
        "open net": "open internet",
        "youtube thurakku": "open youtube",
        "chrome thurakku": "open chrome",
        "browser thurakku": "open internet",
        "entha time": "what time is it",
        "time para": "what time is it",
        "nee ara": "who are you",
        "ninte peru entha": "who are you"
    }

    # Check for exact matches
    if text in exact_mappings:
        return exact_mappings[text]

    # Partial replacements for common misheard phrases (optional but helpful)
    # We apply these if the whole phrase didn't match perfectly.
    partial_replacements = [
        (r'\bturn on lite\b', 'turn on light'),
        (r'\bturn on life\b', 'turn on light'),
        (r'\bturn on right\b', 'turn on light'),
        (r'\bturn of light\b', 'turn off light'),
        (r'\bopen inter net\b', 'open internet')
    ]

    for pattern, replacement in partial_replacements:
        text = re.sub(pattern, replacement, text)

    # Note: We keep the original Malayalam commands mostly intact if they are part of a larger sentence, 
    # but since intent_parser.py ALSO checks for malayalam phrases locally, 
    # this normalizer acts as a fast-track converter for exact voice commands!
    
    return text.strip()
