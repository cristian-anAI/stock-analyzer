#!/usr/bin/env python3
"""
Simple EPUB extractor for Quantitative Trading book
Using ebooklib for better EPUB handling
"""

import os
import re
from pathlib import Path
from datetime import datetime
import zipfile
import html


class SimpleEPUBExtractor:
    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        self.output_dir = Path("books/processed")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_all_text(self):
        """Extract all text from EPUB using simple ZIP extraction"""
        all_text = ""
        
        print(f"Extracting text from: {self.epub_path}")
        
        try:
            with zipfile.ZipFile(self.epub_path, 'r') as epub:
                # List all files in the EPUB
                file_list = epub.namelist()
                print(f"Found {len(file_list)} files in EPUB")
                
                # Filter for HTML/XHTML files (likely content)
                content_files = [f for f in file_list if f.endswith(('.html', '.xhtml', '.htm'))]
                print(f"Found {len(content_files)} content files")
                
                for file_path in content_files:
                    try:
                        print(f"Processing: {file_path}")
                        content = epub.read(file_path)
                        
                        # Decode content
                        if isinstance(content, bytes):
                            text = content.decode('utf-8', errors='ignore')
                        else:
                            text = content
                        
                        # Basic HTML tag removal
                        text = self.clean_html(text)
                        
                        if len(text.strip()) > 50:  # Skip very short content
                            all_text += f"\n\n=== {file_path} ===\n\n"
                            all_text += text
                            all_text += "\n\n"
                            
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error opening EPUB: {e}")
            return None
            
        return all_text
    
    def clean_html(self, html_content: str) -> str:
        """Basic HTML cleaning"""
        import re
        
        # Remove script and style elements
        html_content = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        html_content = re.sub(r'<[^>]+>', ' ', html_content)
        
        # Decode HTML entities
        html_content = html.unescape(html_content)
        
        # Clean up whitespace
        html_content = re.sub(r'\s+', ' ', html_content)
        html_content = re.sub(r'\n\s*\n+', '\n\n', html_content)
        
        return html_content.strip()
    
    def extract_and_save(self):
        """Extract and save content"""
        text = self.extract_all_text()
        
        if text:
            # Save raw extracted text
            raw_file = self.output_dir / "quantitative_trading_raw.txt"
            with open(raw_file, 'w', encoding='utf-8') as f:
                f.write(f"# Quantitative Trading by Ernie Chan\n")
                f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("=" * 80 + "\n\n")
                f.write(text)
            
            print(f"Raw text saved to: {raw_file}")
            print(f"Text length: {len(text)} characters")
            
            # Create organized sections
            self.organize_content(text)
            
            return str(raw_file)
        else:
            print("Failed to extract text from EPUB")
            return None
    
    def organize_content(self, text: str):
        """Organize content into trading categories"""
        print("Organizing content by trading concepts...")
        
        # Define sections to look for
        sections = {
            "mean_reversion": {
                "keywords": ["mean reversion", "z-score", "pairs trading", "cointegration", "ornstein-uhlenbeck"],
                "content": []
            },
            "momentum_strategies": {
                "keywords": ["momentum", "trend following", "breakout", "moving average", "macd"],
                "content": []
            },
            "risk_management": {
                "keywords": ["risk management", "var", "drawdown", "volatility", "stop loss", "position sizing"],
                "content": []
            },
            "backtesting": {
                "keywords": ["backtesting", "walk forward", "out of sample", "overfitting", "bias"],
                "content": []
            },
            "kelly_criterion": {
                "keywords": ["kelly criterion", "optimal bet", "geometric mean", "logarithmic utility"],
                "content": []
            },
            "performance_metrics": {
                "keywords": ["sharpe ratio", "sortino ratio", "calmar ratio", "maximum drawdown", "alpha", "beta"],
                "content": []
            }
        }
        
        # Split text into paragraphs
        paragraphs = text.split('\n\n')
        
        # Categorize paragraphs
        for para in paragraphs:
            if len(para.strip()) < 50:
                continue
                
            para_lower = para.lower()
            
            # Find best matching section
            best_match = None
            max_score = 0
            
            for section_name, section_data in sections.items():
                score = sum(para_lower.count(keyword) for keyword in section_data["keywords"])
                if score > max_score:
                    max_score = score
                    best_match = section_name
            
            # Add to section if good match found
            if best_match and max_score > 0:
                sections[best_match]["content"].append(para.strip())
        
        # Save organized sections
        for section_name, section_data in sections.items():
            if section_data["content"]:
                section_file = self.output_dir / f"{section_name}.txt"
                with open(section_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {section_name.replace('_', ' ').title()}\n")
                    f.write(f"From: Quantitative Trading by Ernie Chan\n")
                    f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("=" * 60 + "\n\n")
                    
                    for i, content in enumerate(section_data["content"], 1):
                        f.write(f"## Section {i}\n\n")
                        f.write(content)
                        f.write("\n\n" + "-" * 40 + "\n\n")
                
                print(f"Created {section_file} with {len(section_data['content'])} sections")
        
        # Create summary
        summary_file = self.output_dir / "extraction_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# Quantitative Trading Knowledge Extraction Summary\n\n")
            f.write(f"Source: {self.epub_path.name}\n")
            f.write(f"Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Organized Sections\n\n")
            for section_name, section_data in sections.items():
                count = len(section_data["content"])
                if count > 0:
                    f.write(f"- **{section_name.replace('_', ' ').title()}**: {count} sections\n")
            
            f.write(f"\n## Files Created\n\n")
            f.write(f"- quantitative_trading_raw.txt (complete extraction)\n")
            for section_name in sections:
                if sections[section_name]["content"]:
                    f.write(f"- {section_name}.txt\n")
        
        print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    epub_path = "books/Quantitative Trading_Ernie_Chan-[Chan, Ernie]--2010 .epub"
    extractor = SimpleEPUBExtractor(epub_path)
    result = extractor.extract_and_save()
    
    if result:
        print(f"\nSuccess! Content extracted to books/processed/")
        print("Ready for Ollama model creation!")
    else:
        print("\nFailed to extract content from EPUB")