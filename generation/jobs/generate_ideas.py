#!/usr/bin/env python3
import sys
import logging
import argparse
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")

from core.logging import setup_json_logging
from generation.clients.claude import ClaudeClient
from generation.schemas import IdeaRequest

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate content ideas using Claude")
    parser.add_argument("--video-id", help="Video ID for context")
    parser.add_argument("--keywords", nargs="+", required=True, help="Keywords for content generation")
    parser.add_argument("--views-per-min", type=float, help="Views per minute signal")
    parser.add_argument("--tone", default="info", help="Content tone (default: info)")
    parser.add_argument("--output", help="Output file path (optional)")

    args = parser.parse_args()

    setup_json_logging()

    trace_id = f"generate_ideas_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    try:
        # Build request
        signals = {}
        if args.views_per_min:
            signals["views_per_min"] = args.views_per_min

        request = IdeaRequest(
            video_id=args.video_id,
            keywords=args.keywords,
            signals=signals,
            style={
                "tone": args.tone,
                "language": "ko",
                "length_sec": "20"
            }
        )

        logger.info(f"Starting idea generation", extra={
            "trace_id": trace_id,
            "keywords": args.keywords,
            "video_id": args.video_id
        })

        # Generate ideas
        with ClaudeClient() as claude:
            response = claude.generate_ideas(request, trace_id)

        # Prepare output
        output_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request.dict(),
            "response": response.dict()
        }

        json_output = json.dumps(output_data, indent=2, ensure_ascii=False)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Ideas saved to {args.output}")
        else:
            print(json_output)

        logger.info(f"Idea generation completed", extra={
            "trace_id": trace_id,
            "titles_count": len(response.titles),
            "tags_count": len(response.tags)
        })

    except Exception as e:
        logger.error(f"Idea generation failed: {e}", extra={"trace_id": trace_id})
        raise

if __name__ == "__main__":
    main()