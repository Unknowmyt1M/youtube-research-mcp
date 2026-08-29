import re
from typing import List, Optional
from youtube_research_mcp.models.transcript import TranscriptChunk, TranscriptSegment
from youtube_research_mcp.models.video import Chapter
from youtube_research_mcp.utils.formatting import (
    format_timestamp,
    make_timestamp_url,
)


class TranscriptChunker:
    """Timestamp-preserving semantic chunker for long YouTube transcripts."""

    def __init__(self, target_words: int = 180, overlap_words: int = 30):
        self.target_words = target_words
        self.overlap_words = overlap_words
        self.sentence_end = re.compile(r"[\.!\?]\s*|\n+")

    def chunk_segments(
        self,
        segments: List[TranscriptSegment],
        video_id: str,
        chapters: Optional[List[Chapter]] = None,
    ) -> List[TranscriptChunk]:
        """Alias for chunk_transcript matching kwargs."""
        return self.chunk_transcript(
            video_id=video_id, segments=segments, chapters=chapters
        )

    def chunk_transcript(
        self,
        video_id: str,
        segments: List[TranscriptSegment],
        chapters: Optional[List[Chapter]] = None,
    ) -> List[TranscriptChunk]:
        """Group raw subtitle segments into coherent, timestamp-aware chunks."""
        if not segments:
            return []

        chunks: List[TranscriptChunk] = []
        current_chunk_segments: List[TranscriptSegment] = []
        current_word_count = 0
        chunk_idx = 1

        for seg in segments:
            seg_words = len(seg.text.split())
            current_chunk_segments.append(seg)
            current_word_count += seg_words

            # Check if target word count reached AND is near a sentence/clause end
            is_sentence_boundary = bool(self.sentence_end.search(seg.text))
            if current_word_count >= self.target_words and is_sentence_boundary:
                chunk = self._create_chunk(
                    video_id, chunk_idx, current_chunk_segments, chapters
                )
                chunks.append(chunk)
                chunk_idx += 1

                # Calculate overlap segments
                overlap_segments: List[TranscriptSegment] = []
                overlap_count = 0
                for s in reversed(current_chunk_segments):
                    overlap_segments.insert(0, s)
                    overlap_count += len(s.text.split())
                    if overlap_count >= self.overlap_words:
                        break

                current_chunk_segments = overlap_segments
                current_word_count = sum(len(s.text.split()) for s in current_chunk_segments)

        # Flush remaining segments
        if current_chunk_segments:
            chunk = self._create_chunk(
                video_id, chunk_idx, current_chunk_segments, chapters
            )
            chunks.append(chunk)

        return chunks

    def _create_chunk(
        self,
        video_id: str,
        index: int,
        segments: List[TranscriptSegment],
        chapters: Optional[List[Chapter]] = None,
    ) -> TranscriptChunk:
        start_sec = segments[0].start
        end_sec = segments[-1].end
        combined_text = " ".join(s.text for s in segments)
        word_count = len(combined_text.split())

        start_fmt = format_timestamp(start_sec)
        end_fmt = format_timestamp(end_sec)

        # Match enclosing chapter title if chapters are available
        chapter_title = None
        if chapters:
            for ch in chapters:
                if ch.start_seconds <= start_sec:
                    if ch.end_seconds is None or start_sec < ch.end_seconds:
                        chapter_title = ch.title

        return TranscriptChunk(
            chunk_id=f"{video_id}_c{index:03d}",
            video_id=video_id,
            start_seconds=start_sec,
            end_seconds=end_sec,
            start_formatted=start_fmt,
            end_formatted=end_fmt,
            time_range=f"{start_fmt} - {end_fmt}",
            text=combined_text,
            url=make_timestamp_url(video_id, start_sec),
            chapter_title=chapter_title,
            word_count=word_count,
        )
