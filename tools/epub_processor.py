#!/usr/bin/env python3
"""
EPUB to Trading Knowledge Processor
Converts Ernie Chan's "Quantitative Trading" EPUB into structured training data
for specialized Ollama trading model.
"""

import os
import re
import zipfile
from pathlib import Path
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET
import html2text
from datetime import datetime


class EPUBProcessor:
    def __init__(self, epub_path: str, output_dir: str = "books/processed"):
        self.epub_path = Path(epub_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create category directories
        self.categories = {
            "mean_reversion_strategies": "Mean Reversion Trading Strategies",
            "momentum_strategies": "Momentum and Trend Following",
            "risk_management": "Risk Management and Position Sizing",
            "backtesting_methods": "Backtesting Methodology",
            "portfolio_theory": "Portfolio Theory and Optimization",
            "statistical_arbitrage": "Statistical Arbitrage Strategies",
            "kelly_criterion": "Kelly Criterion and Bet Sizing",
            "performance_metrics": "Performance Measurement and Metrics"
        }
        
        for category in self.categories.keys():
            (self.output_dir / category).mkdir(exist_ok=True)
        
        # HTML to text converter
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.ignore_images = True
        self.h2t.ignore_emphasis = False
        self.h2t.body_width = 0  # No line wrapping
        
        # Keywords for categorization
        self.keyword_mapping = {
            "mean_reversion_strategies": [
                "mean reversion", "z-score", "pairs trading", "bollinger bands", 
                "reversal", "cointegration", "ornstein-uhlenbeck", "equilibrium",
                "adf test", "hurst exponent", "autocorrelation"
            ],
            "momentum_strategies": [
                "momentum", "trend following", "breakout", "moving average",
                "macd", "rsi", "trend", "directional", "price acceleration"
            ],
            "risk_management": [
                "risk management", "var", "value at risk", "drawdown", "volatility",
                "stop loss", "position sizing", "leverage", "margin",
                "maximum adverse excursion", "mae"
            ],
            "backtesting_methods": [
                "backtesting", "walk forward", "out of sample", "data snooping",
                "overfitting", "bias", "survivorship bias", "look ahead bias",
                "monte carlo", "bootstrap"
            ],
            "portfolio_theory": [
                "portfolio optimization", "markowitz", "efficient frontier",
                "correlation", "diversification", "capital allocation"
            ],
            "statistical_arbitrage": [
                "statistical arbitrage", "stat arb", "pairs trading",
                "market neutral", "dollar neutral", "beta neutral"
            ],
            "kelly_criterion": [
                "kelly criterion", "optimal bet size", "geometric mean",
                "logarithmic utility", "growth optimal"
            ],
            "performance_metrics": [
                "sharpe ratio", "sortino ratio", "calmar ratio", "maximum drawdown",
                "information ratio", "alpha", "beta", "tracking error"
            ]
        }

    def extract_epub(self) -> dict:
        """Extract EPUB content and organize by chapters"""
        content = {}
        
        with zipfile.ZipFile(self.epub_path, 'r') as epub:
            # Get the container XML to find the OPF file
            container = epub.read('META-INF/container.xml')
            container_root = ET.fromstring(container)
            
            # Find OPF file path
            opf_path = container_root.find('.//{urn:oasis:names:tc:opendocument:xmlns:container}rootfile').get('full-path')
            
            # Parse OPF to get spine order
            opf_content = epub.read(opf_path)
            opf_root = ET.fromstring(opf_content)
            
            # Get spine order
            spine = opf_root.find('.//{http://www.idpf.org/2007/opf}spine')
            manifest = opf_root.find('.//{http://www.idpf.org/2007/opf}manifest')
            
            # Build manifest lookup
            manifest_lookup = {}
            for item in manifest.findall('.//{http://www.idpf.org/2007/opf}item'):
                manifest_lookup[item.get('id')] = item.get('href')
            
            # Extract content in spine order
            opf_dir = os.path.dirname(opf_path)
            chapter_num = 1
            
            for itemref in spine.findall('.//{http://www.idpf.org/2007/opf}itemref'):
                idref = itemref.get('idref')
                if idref in manifest_lookup:
                    file_path = os.path.join(opf_dir, manifest_lookup[idref]) if opf_dir else manifest_lookup[idref]
                    
                    try:
                        html_content = epub.read(file_path)
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # Extract title
                        title_elem = soup.find(['h1', 'h2', 'title'])
                        title = title_elem.get_text().strip() if title_elem else f"Chapter {chapter_num}"
                        
                        # Convert to clean text
                        text_content = self.h2t.handle(str(soup))
                        
                        # Clean up the text
                        text_content = self.clean_text(text_content)
                        
                        if len(text_content.strip()) > 100:  # Skip very short content
                            content[f"chapter_{chapter_num:02d}_{self.sanitize_filename(title)}"] = {
                                "title": title,
                                "content": text_content,
                                "file_path": file_path
                            }
                            chapter_num += 1
                            
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        continue
        
        return content

    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Preserve mathematical formulas
        # Keep equations that look like: E(R) = μ, σ² = variance, etc.
        text = re.sub(r'(\w+)\s*=\s*([^,\n]+)', r'\1 = \2', text)
        
        # Clean up common artifacts
        text = text.replace('* * *', '---')
        text = text.replace('**', '')
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove markdown links
        
        return text.strip()

    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem"""
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)
        filename = filename[:50]  # Limit length
        return filename.lower()

    def categorize_content(self, content: dict) -> dict:
        """Categorize content based on keywords and topics"""
        categorized = {cat: [] for cat in self.categories.keys()}
        uncategorized = []
        
        for chapter_id, chapter_data in content.items():
            text = chapter_data["content"].lower()
            title = chapter_data["title"].lower()
            
            # Count keyword matches for each category
            matches = {}
            for category, keywords in self.keyword_mapping.items():
                count = 0
                for keyword in keywords:
                    count += text.count(keyword) + title.count(keyword) * 2  # Title matches weighted more
                matches[category] = count
            
            # Assign to category with most matches
            if max(matches.values()) > 0:
                best_category = max(matches, key=matches.get)
                categorized[best_category].append({
                    "chapter_id": chapter_id,
                    "title": chapter_data["title"],
                    "content": chapter_data["content"],
                    "match_score": matches[best_category]
                })
            else:
                uncategorized.append(chapter_data)
        
        # Handle uncategorized content
        if uncategorized:
            categorized["general"] = uncategorized
        
        return categorized

    def extract_key_elements(self, text: str) -> dict:
        """Extract trading rules, formulas, and metrics from text"""
        elements = {
            "trading_rules": [],
            "formulas": [],
            "risk_metrics": [],
            "implementation_notes": [],
            "backtesting_warnings": []
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Trading rules - look for imperatives and strategies
            if any(word in line_lower for word in ['buy when', 'sell when', 'enter', 'exit', 'strategy:', 'rule:']):
                elements["trading_rules"].append(line.strip())
            
            # Mathematical formulas - look for equations
            if re.search(r'[=<>≥≤]', line) and any(char.isalpha() for char in line):
                elements["formulas"].append(line.strip())
            
            # Risk metrics
            if any(metric in line_lower for metric in ['sharpe', 'var', 'drawdown', 'volatility', 'risk']):
                elements["risk_metrics"].append(line.strip())
            
            # Implementation notes
            if any(word in line_lower for word in ['note:', 'important:', 'remember:', 'implementation']):
                elements["implementation_notes"].append(line.strip())
            
            # Backtesting warnings
            if any(word in line_lower for word in ['bias', 'overfitting', 'warning:', 'careful', 'avoid']):
                elements["backtesting_warnings"].append(line.strip())
        
        return elements

    def process_epub(self) -> str:
        """Main processing pipeline"""
        print(f"Processing EPUB: {self.epub_path}")
        
        # Step 1: Extract content
        print("Step 1: Extracting EPUB content...")
        content = self.extract_epub()
        print(f"Extracted {len(content)} chapters")
        
        # Step 2: Categorize content
        print("Step 2: Categorizing content...")
        categorized = self.categorize_content(content)
        
        # Step 3: Save categorized content and extract key elements
        print("Step 3: Saving categorized content...")
        all_elements = {}
        
        for category, chapters in categorized.items():
            if not chapters:
                continue
                
            category_dir = self.output_dir / category
            category_file = category_dir / f"{category}.txt"
            
            with open(category_file, 'w', encoding='utf-8') as f:
                f.write(f"# {self.categories.get(category, category.replace('_', ' ').title())}\n\n")
                f.write(f"Extracted from: Quantitative Trading by Ernie Chan\n")
                f.write(f"Processing date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("=" * 80 + "\n\n")
                
                category_elements = {
                    "trading_rules": [],
                    "formulas": [],
                    "risk_metrics": [],
                    "implementation_notes": [],
                    "backtesting_warnings": []
                }
                
                for chapter in chapters:
                    f.write(f"## {chapter['title']}\n\n")
                    f.write(chapter['content'])
                    f.write("\n\n" + "=" * 40 + "\n\n")
                    
                    # Extract key elements
                    elements = self.extract_key_elements(chapter['content'])
                    for key in category_elements:
                        category_elements[key].extend(elements[key])
                
                # Write summary of key elements
                f.write("# KEY ELEMENTS SUMMARY\n\n")
                for element_type, items in category_elements.items():
                    if items:
                        f.write(f"## {element_type.replace('_', ' ').title()}\n\n")
                        for item in set(items):  # Remove duplicates
                            f.write(f"- {item}\n")
                        f.write("\n")
                
                all_elements[category] = category_elements
        
        # Create master summary
        summary_file = self.output_dir / "MASTER_SUMMARY.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# QUANTITATIVE TRADING KNOWLEDGE EXTRACTION\n")
            f.write(f"Source: {self.epub_path.name}\n")
            f.write(f"Processed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## CATEGORIES PROCESSED\n\n")
            for category, description in self.categories.items():
                chapter_count = len(categorized.get(category, []))
                f.write(f"- **{description}** ({chapter_count} chapters) -> {category}.txt\n")
            
            f.write("\n## GLOBAL KEY ELEMENTS\n\n")
            global_elements = {key: [] for key in ["trading_rules", "formulas", "risk_metrics", "implementation_notes", "backtesting_warnings"]}
            
            for category_elements in all_elements.values():
                for key in global_elements:
                    global_elements[key].extend(category_elements[key])
            
            for element_type, items in global_elements.items():
                if items:
                    f.write(f"### {element_type.replace('_', ' ').title()} ({len(set(items))} unique)\n\n")
                    for item in sorted(set(items)):
                        f.write(f"- {item}\n")
                    f.write("\n")
        
        print(f"Processing complete! Output saved to: {self.output_dir}")
        print(f"Categories processed: {len([c for c in categorized.values() if c])}")
        print(f"Master summary: {summary_file}")
        
        return str(self.output_dir)


if __name__ == "__main__":
    # Process the Quantitative Trading book
    epub_path = "books/Quantitative Trading_Ernie_Chan-[Chan, Ernie]--2010 .epub"
    
    processor = EPUBProcessor(epub_path)
    output_dir = processor.process_epub()
    
    print(f"\n✅ EPUB processing complete!")
    print(f"📁 Output directory: {output_dir}")
    print(f"📖 Ready for Ollama model creation!")