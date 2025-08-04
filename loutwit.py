#!/usr/bin/env -S python3
# -*- coding: utf-8 -*-
"""
Selik Vocabulary Analyzer
Analyzes Selik vocabulary files to find duplicate definitions and undefined words.
"""

import sys
import re
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Set, Tuple, NamedTuple


class VocabEntry(NamedTuple):
    """Represents a vocabulary entry with all its components."""
    line_number: int
    original_line: str
    selik_word: str  # Empty string if undefined
    chinese_meaning: str
    part_of_speech: str  # Empty string if no POS specified
    is_defined: bool
    file_path: str


class VocabAnalyzer:
    """Analyzes Selik vocabulary files for duplicates and undefined entries."""
    
    def __init__(self):
        self.entries: List[VocabEntry] = []
        # Track duplicates: key -> list of entries
        self.selik_duplicates: Dict[str, List[VocabEntry]] = defaultdict(list)
        self.meaning_duplicates: Dict[Tuple[str, str], List[VocabEntry]] = defaultdict(list)
        self.undefined_entries: List[VocabEntry] = []
    
    def parse_line(self, line: str, line_number: int, file_path: str) -> VocabEntry:
        """
        Parse a single vocabulary line into its components.
        
        Expected formats:
        - Defined: "1. selik_word chinese_meaning"
        - Defined with POS: "1. selik_word chinese_meaning pos"  
        - Undefined: "1. chinese_meaning pos"
        - Multi-word Selik: "1. selik_word1 selik_word2 chinese_meaning"
        """
        # Remove leading/trailing whitespace and number prefix
        clean_line = re.sub(r'^\s*\d+\.\s*', '', line.strip())
        
        if not clean_line:
            return VocabEntry(line_number, line, "", "", "", False, file_path)
        
        # Split the line into components
        parts = clean_line.split()
        
        if len(parts) == 0:
            return VocabEntry(line_number, line, "", "", "", False, file_path)
        
        # Check if this line appears to be undefined by looking for patterns
        # Undefined lines typically have Chinese characters immediately followed by POS
        # or just Chinese characters without Selik words
        
        # Find the first part that looks like Chinese characters
        chinese_start_idx = None
        for i, part in enumerate(parts):
            # If this part contains Chinese characters, it's likely the start of meaning
            if self._contains_chinese(part):
                chinese_start_idx = i
                break
        
        if chinese_start_idx is None:
            # No Chinese found, treat as undefined with unknown meaning
            return VocabEntry(line_number, line, "", clean_line, "", False, file_path)
        
        # If Chinese starts at index 0, this is likely undefined
        if chinese_start_idx == 0:
            # Check if last part is a part of speech marker
            last_part = parts[-1]
            if self._is_pos_marker(last_part):
                chinese_meaning = ' '.join(parts[:-1])
                pos = last_part
            else:
                chinese_meaning = clean_line
                pos = ""
            
            return VocabEntry(line_number, line, "", chinese_meaning, pos, False, file_path)
        
        # Otherwise, everything before the Chinese is Selik word(s)
        selik_parts = parts[:chinese_start_idx]
        meaning_parts = parts[chinese_start_idx:]
        
        # Check if last part of meaning is POS
        if len(meaning_parts) > 1 and self._is_pos_marker(meaning_parts[-1]):
            chinese_meaning = ' '.join(meaning_parts[:-1])
            pos = meaning_parts[-1]
        else:
            chinese_meaning = ' '.join(meaning_parts)
            pos = ""
        
        selik_word = ' '.join(selik_parts)
        
        return VocabEntry(line_number, line, selik_word, chinese_meaning, pos, True, file_path)
    
    def _contains_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':  # CJK Unified Ideographs
                return True
        return False
    
    def _is_pos_marker(self, text: str) -> bool:
        """Check if text appears to be a part-of-speech marker."""
        pos_markers = {'v.', 'n.', 'adj.', 'adv.', 'prep.', 'conj.', 'interj.', 'pron.'}
        return text.lower() in pos_markers or text in pos_markers
    
    def load_file(self, file_path: str) -> int:
        """Load and parse a vocabulary file. Returns number of entries loaded."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            entries_loaded = 0
            for line_num, line in enumerate(lines, 1):
                if line.strip():  # Skip empty lines
                    entry = self.parse_line(line, line_num, file_path)
                    self.entries.append(entry)
                    entries_loaded += 1
            
            print(f"Loaded {entries_loaded} entries from {file_path}")
            return entries_loaded
            
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            return 0
        except UnicodeDecodeError:
            print(f"Error: Could not decode file '{file_path}'. Please ensure it's UTF-8 encoded.")
            return 0
        except Exception as e:
            print(f"Error loading file '{file_path}': {e}")
            return 0
    
    def analyze(self):
        """Analyze all loaded entries for duplicates and undefined words."""
        print("\nAnalyzing vocabulary entries...")
        
        # Separate defined and undefined entries
        defined_entries = [e for e in self.entries if e.is_defined]
        self.undefined_entries = [e for e in self.entries if not e.is_defined]
        
        print(f"Found {len(defined_entries)} defined entries and {len(self.undefined_entries)} undefined entries.")
        
        # Find Selik word duplicates (only among defined entries)
        for entry in defined_entries:
            if entry.selik_word:  # Skip entries without Selik words
                self.selik_duplicates[entry.selik_word].append(entry)
        
        # Find meaning duplicates (considering part of speech)
        for entry in defined_entries:
            # Create a key that includes both meaning and part of speech
            meaning_key = (entry.chinese_meaning, entry.part_of_speech)
            self.meaning_duplicates[meaning_key].append(entry)
        
        # Remove non-duplicates (entries that appear only once)
        self.selik_duplicates = {k: v for k, v in self.selik_duplicates.items() if len(v) > 1}
        self.meaning_duplicates = {k: v for k, v in self.meaning_duplicates.items() if len(v) > 1}
    
    def print_results(self):
        """Print analysis results in a formatted way."""
        print("\n" + "="*80)
        print("SELIK VOCABULARY ANALYSIS RESULTS")
        print("="*80)
        
        # Print undefined entries
        if self.undefined_entries:
            print(f"\n🚨 UNDEFINED ENTRIES ({len(self.undefined_entries)} found):")
            print("-" * 50)
            for entry in self.undefined_entries:
                pos_info = f" [{entry.part_of_speech}]" if entry.part_of_speech else ""
                print(f"  📁 {entry.file_path}:{entry.line_number}")
                print(f"     ❌ {entry.chinese_meaning}{pos_info}")
                print(f"     📝 Original: {entry.original_line.strip()}")
                print()
        else:
            print("\n✅ No undefined entries found!")
        
        # Print Selik word duplicates
        if self.selik_duplicates:
            print(f"\n🔄 DUPLICATE SELIK WORDS ({len(self.selik_duplicates)} found):")
            print("-" * 50)
            for selik_word, entries in self.selik_duplicates.items():
                print(f"  🔤 Selik word: '{selik_word}' appears {len(entries)} times:")
                for entry in entries:
                    pos_info = f" [{entry.part_of_speech}]" if entry.part_of_speech else ""
                    print(f"     📁 {entry.file_path}:{entry.line_number} → {entry.chinese_meaning}{pos_info}")
                print()
        else:
            print("\n✅ No duplicate Selik words found!")
        
        # Print meaning duplicates
        if self.meaning_duplicates:
            print(f"\n🔄 DUPLICATE MEANINGS ({len(self.meaning_duplicates)} found):")
            print("-" * 50)
            for (meaning, pos), entries in self.meaning_duplicates.items():
                pos_info = f" [{pos}]" if pos else ""
                print(f"  🇨🇳 Meaning: '{meaning}{pos_info}' appears {len(entries)} times:")
                for entry in entries:
                    print(f"     📁 {entry.file_path}:{entry.line_number} → {entry.selik_word}")
                print()
        else:
            print("\n✅ No duplicate meanings found!")
        
        # Print summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total entries processed: {len(self.entries)}")
        print(f"Undefined entries: {len(self.undefined_entries)}")
        print(f"Duplicate Selik words: {len(self.selik_duplicates)}")
        print(f"Duplicate meanings: {len(self.meaning_duplicates)}")
        
        if self.undefined_entries or self.selik_duplicates or self.meaning_duplicates:
            print(f"\n⚠️  Issues found! Please review the entries above.")
        else:
            print(f"\n🎉 All entries are properly defined and unique!")


def main():
    """Main function to run the vocabulary analyzer."""
    if len(sys.argv) < 2:
        print("Usage: python selik_analyzer.py <vocab_file1> [vocab_file2] ...")
        print("\nExample: python selik_analyzer.py vocabulary.txt additional_words.txt")
        return
    
    analyzer = VocabAnalyzer()
    
    # Load all specified files
    total_entries = 0
    for file_path in sys.argv[1:]:
        if Path(file_path).exists():
            entries = analyzer.load_file(file_path)
            total_entries += entries
        else:
            print(f"Warning: File '{file_path}' does not exist, skipping...")
    
    if total_entries == 0:
        print("No entries loaded. Please check your file paths.")
        return
    
    # Analyze the vocabulary
    analyzer.analyze()
    analyzer.print_results()


if __name__ == "__main__":
    main()