#!/usr/bin/env python3
import sys
import logging
import argparse
import json
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, ".")

from core.logging import setup_json_logging
from generation.clients.model_client import StubModelClient
from generation.schemas.idea import IdeaRequest

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Generate content ideas using Claude")
    parser.add_argument("--video-id", help="Video ID for context")
    parser.add_argument("--keywords", nargs="+", default=["트렌드"], help="Keywords for content generation")
    parser.add_argument("--signals", help="JSON string of analysis signals")
    parser.add_argument("--style", help="JSON string of generation style")
    parser.add_argument("--out-file", help="Output file path (optional)")

    args = parser.parse_args()

    setup_json_logging()

    trace_id = f"generate_ideas_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    try:
        # Build request
        import json as json_lib

        signals = {}
        if args.signals:
            signals = json_lib.loads(args.signals)

        style = {
            "tone": "info",
            "language": "ko",
            "length_sec": "20"
        }
        if args.style:
            style.update(json_lib.loads(args.style))

        request = IdeaRequest(
            video_id=args.video_id,
            keywords=args.keywords,
            signals=signals,
            style=style
        )

        logger.info(f"Starting idea generation", extra={
            "trace_id": trace_id,
            "job": "generate_ideas",
            "keywords": args.keywords,
            "video_id": args.video_id
        })

        # Generate ideas
        client = StubModelClient()  # Use stub for v1
        response = client.generate_ideas(request, trace_id)

        # Prepare output
        output_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request": request.model_dump(),
            "response": response.model_dump()
        }

        json_output = json.dumps(output_data, indent=2, ensure_ascii=False)

        if args.out_file:
            with open(args.out_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Ideas saved to {args.out_file}")
        else:
            print(json_output)

        logger.info(f"Idea generation completed", extra={
            "trace_id": trace_id,
            "job": "generate_ideas",
            "titles_count": len(response.titles),
            "tags_count": len(response.tags)
        })

    except Exception as e:
        logger.error(f"Idea generation failed: {e}", extra={
            "trace_id": trace_id,
            "job": "generate_ideas"
        })
        raise

if __name__ == "__main__":
    main()