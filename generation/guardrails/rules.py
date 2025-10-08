"""Guardrails validation rules for content generation"""
import re
from typing import List, Dict, Any

def validate_titles(titles: List[str]) -> List[str]:
    """Validate titles against guardrails rules"""
    violations = []

    for i, title in enumerate(titles):
        # Length check (20-35 chars)
        if not 20 <= len(title) <= 35:
            violations.append(f"Title {i+1} length {len(title)} not in range 20-35: {title}")

        # Emoji count check (≤ 1)
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        emoji_count = len(re.findall(emoji_pattern, title))
        if emoji_count > 1:
            violations.append(f"Title {i+1} has {emoji_count} emojis (max 1): {title}")

        # Forbidden clickbait patterns
        forbidden_words = ['클릭', '충격', '경악', '실화', '미친', '대박', '레전드', '역대급']
        found_forbidden = [word for word in forbidden_words if word in title]
        if found_forbidden:
            violations.append(f"Title {i+1} contains forbidden words {found_forbidden}: {title}")

        # Number abuse check
        number_count = len(re.findall(r'\d+', title))
        if number_count > 2:
            violations.append(f"Title {i+1} has excessive numbers ({number_count}): {title}")

    return violations

def validate_tags(tags: List[str]) -> List[str]:
    """Validate tags against guardrails rules"""
    violations = []

    # Check core tags (first 3 should be core keywords)
    if len(tags) < 5:
        violations.append(f"Need at least 5 tags, got {len(tags)}")

    for i, tag in enumerate(tags):
        # Must start with #
        if not tag.startswith('#'):
            violations.append(f"Tag {i+1} must start with #: {tag}")

        # Length check (2-20 chars after #)
        tag_content = tag[1:] if tag.startswith('#') else tag
        if not 2 <= len(tag_content) <= 20:
            violations.append(f"Tag {i+1} length invalid: {tag}")

        # No PII or forbidden content
        forbidden_content = ['개인정보', '전화번호', '이메일', '주소', '실명']
        found_forbidden = [word for word in forbidden_content if word in tag]
        if found_forbidden:
            violations.append(f"Tag {i+1} contains forbidden content {found_forbidden}: {tag}")

    # Check for duplicate tags
    unique_tags = set(tags)
    if len(unique_tags) != len(tags):
        violations.append(f"Duplicate tags found: {len(tags)} total, {len(unique_tags)} unique")

    return violations

def validate_script_beats(script_beats: Dict[str, Any]) -> List[str]:
    """Validate script beats for 3-Beat structure"""
    violations = []

    required_beats = ['hook', 'body', 'cta']
    for beat in required_beats:
        if beat not in script_beats:
            violations.append(f"Missing required script beat: {beat}")
            continue

        content = script_beats[beat]
        if not isinstance(content, str):
            violations.append(f"Script beat {beat} must be string")
            continue

        # Check for factual basis requirement
        speculation_words = ['추측', '아마도', '예상', '카더라', '소문']
        found_speculation = [word for word in speculation_words if word in content]
        if found_speculation:
            violations.append(f"Script {beat} contains speculation words {found_speculation}")

    return violations