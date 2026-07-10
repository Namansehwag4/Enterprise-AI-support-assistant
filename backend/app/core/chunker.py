from typing import List

class RecursiveCharacterTextSplitter:
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: List[str] = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def split_text(self, text: str) -> List[str]:
        # Split text recursively
        splits = self._split(text, self.separators)
        
        # Merge splits into chunks of size self.chunk_size with overlap
        chunks = []
        current_doc = []
        current_len = 0
        
        for split in splits:
            split_len = len(split)
            if current_len + split_len > self.chunk_size:
                if current_doc:
                    chunks.append("".join(current_doc))
                    # Retain overlap: take last few pieces that fit within overlap size
                    overlap_doc = []
                    overlap_len = 0
                    for d in reversed(current_doc):
                        if overlap_len + len(d) <= self.chunk_overlap:
                            overlap_doc.insert(0, d)
                            overlap_len += len(d)
                        else:
                            break
                    current_doc = overlap_doc
                    current_len = overlap_len
            
            current_doc.append(split)
            current_len += split_len
            
        if current_doc:
            chunks.append("".join(current_doc))
            
        return [c.strip() for c in chunks if c.strip()]

    def _split(self, text: str, separators: List[str]) -> List[str]:
        if not separators:
            return [text]
            
        separator = separators[0]
        next_separators = separators[1:]
        
        # Split by the separator but keep it if it is newline or space
        parts = []
        if separator == "":
            return list(text)
            
        splits = text.split(separator)
        for i, s in enumerate(splits):
            if i < len(splits) - 1:
                parts.append(s + separator)
            else:
                parts.append(s)
                
        final_splits = []
        for part in parts:
            if len(part) <= self.chunk_size:
                final_splits.append(part)
            else:
                # Recursively split the long part with the remaining separators
                final_splits.extend(self._split(part, next_separators))
                
        return final_splits
