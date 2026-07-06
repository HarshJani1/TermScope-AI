"""
Helper Utilities
Timestamp formatting and markdown transcript generation.
"""

from datetime import datetime, timezone


def now_utc():
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_timestamp(dt):
    """Format a datetime for display."""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_transcript_markdown(document, conversations):
    """
    Generate a markdown-formatted transcript for a document's conversation.

    Args:
        document: Document model instance.
        conversations: List of Conversation model instances.

    Returns:
        Markdown-formatted transcript string.
    """
    lines = [
        f"# TermScope — Document Analysis Transcript",
        f"",
        f"**Document:** {document.original_filename}",
        f"**Uploaded:** {format_timestamp(document.created_at)}",
        f"**Status:** {document.status}",
        f"",
        f"---",
        f"",
    ]

    if document.llm_response:
        lines.extend([
            f"## Initial Analysis",
            f"*Generated at: {format_timestamp(document.updated_at)}*",
            f"",
            document.llm_response,
            f"",
            f"---",
            f"",
        ])

    if conversations:
        lines.extend([f"## Follow-up Q&A", f""])
        for conv in conversations:
            timestamp = format_timestamp(conv.created_at)
            if conv.role == "user":
                lines.extend([
                    f"### 🧑 User — *{timestamp}*",
                    f"",
                    conv.content,
                    f"",
                ])
            elif conv.role == "assistant":
                lines.extend([
                    f"### 🤖 TermScope AI — *{timestamp}*",
                    f"",
                    conv.content,
                    f"",
                    f"---",
                    f"",
                ])

    return "\n".join(lines)
