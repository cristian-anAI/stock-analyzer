#!/usr/bin/env python3
"""
Advanced Trading Knowledge Extractor
Specifically designed to extract actionable trading knowledge from Ernie Chan's book
for integration into specialized Ollama trading model.
"""

import re
from pathlib import Path
from datetime import datetime


class TradingKnowledgeExtractor:
    def __init__(self, raw_text_file: str = "books/processed/quantitative_trading_raw.txt"):
        self.raw_text_file = Path(raw_text_file)
        self.output_dir = Path("books/processed/trading_knowledge")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load the raw text
        with open(self.raw_text_file, 'r', encoding='utf-8') as f:
            self.text = f.read()
    
    def extract_formulas_and_equations(self) -> list:
        """Extract mathematical formulas and trading equations"""
        formulas = []
        
        # Pattern for equations with equals sign
        equation_patterns = [
            r'([A-Za-z_][A-Za-z0-9_]*\s*=\s*[^,\n\.]+)',  # Variable = expression
            r'(g\s*=\s*[^,\n\.]+)',  # Growth rate formulas
            r'(f\s*\*?\s*=\s*[^,\n\.]+)',  # Kelly formula variations
            r'(Sharpe\s+ratio\s*=\s*[^,\n\.]+)',  # Sharpe ratio
            r'(return\s*=\s*[^,\n\.]+)',  # Return formulas
        ]
        
        for pattern in equation_patterns:
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip().replace('\n', ' ').replace('  ', ' ')
                if len(cleaned) > 5 and len(cleaned) < 200:  # Reasonable length
                    formulas.append(cleaned)
        
        # Look for specific Kelly formula variations
        kelly_patterns = [
            r'f\s*\*?\s*=\s*m\s*/\s*s\s*\^?\s*2',
            r'Kelly\s+formula[^\.]*',
            r'optimal\s+leverage[^\.]*',
            r'F\*\s*=\s*C\^-1\s*M',
        ]
        
        for pattern in kelly_patterns:
            matches = re.findall(pattern, self.text, re.IGNORECASE | re.DOTALL)
            formulas.extend([m.strip() for m in matches if len(m.strip()) > 10])
        
        return list(set(formulas))  # Remove duplicates
    
    def extract_trading_rules(self) -> list:
        """Extract explicit trading rules and strategies"""
        rules = []
        
        # Look for trading rules
        rule_indicators = [
            r'(buy\s+when[^\.]+)',
            r'(sell\s+when[^\.]+)',
            r'(enter\s+[^\.]+position[^\.]*)',
            r'(exit\s+[^\.]+position[^\.]*)',
            r'(strategy\s*:\s*[^\.]+)',
            r'(rule\s*\d*\s*:\s*[^\.]+)',
            r'(if[^\.]*then[^\.]*)',
            r'(should\s+[^\.]*buy[^\.]*)',
            r'(should\s+[^\.]*sell[^\.]*)',
            r'(recommend[^\.]*position[^\.]*)',
        ]
        
        for pattern in rule_indicators:
            matches = re.findall(pattern, self.text, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip().replace('\n', ' ').replace('  ', ' ')
                if len(cleaned) > 10 and len(cleaned) < 300:
                    rules.append(cleaned)
        
        return list(set(rules))
    
    def extract_risk_management_concepts(self) -> list:
        """Extract risk management principles"""
        risk_concepts = []
        
        # Split text into sentences for better extraction
        sentences = re.split(r'[.!?]+', self.text)
        
        risk_keywords = [
            'risk management', 'drawdown', 'stop loss', 'position sizing',
            'leverage', 'var', 'value at risk', 'maximum adverse excursion',
            'kelly', 'half-kelly', 'volatility', 'sharpe ratio'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
                
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in risk_keywords):
                risk_concepts.append(sentence)
        
        return list(set(risk_concepts))
    
    def extract_backtesting_principles(self) -> list:
        """Extract backtesting methodology and warnings"""
        backtest_concepts = []
        
        sentences = re.split(r'[.!?]+', self.text)
        
        backtest_keywords = [
            'backtest', 'overfitting', 'data snooping', 'survivorship bias',
            'look ahead bias', 'out of sample', 'walk forward', 'monte carlo',
            'bootstrap', 'bias', 'curve fitting'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
                
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in backtest_keywords):
                backtest_concepts.append(sentence)
        
        return list(set(backtest_concepts))
    
    def extract_performance_metrics(self) -> list:
        """Extract performance measurement concepts"""
        metrics = []
        
        sentences = re.split(r'[.!?]+', self.text)
        
        metric_keywords = [
            'sharpe ratio', 'sortino ratio', 'calmar ratio', 'information ratio',
            'alpha', 'beta', 'tracking error', 'maximum drawdown',
            'compounded growth', 'geometric mean', 'arithmetic mean'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
                
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in metric_keywords):
                metrics.append(sentence)
        
        return list(set(metrics))
    
    def extract_mean_reversion_concepts(self) -> list:
        """Extract mean reversion trading concepts"""
        concepts = []
        
        sentences = re.split(r'[.!?]+', self.text)
        
        mr_keywords = [
            'mean reversion', 'z-score', 'pairs trading', 'cointegration',
            'ornstein-uhlenbeck', 'equilibrium', 'adf test', 'hurst exponent',
            'autocorrelation', 'statistical arbitrage', 'spread'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
                
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in mr_keywords):
                concepts.append(sentence)
        
        return list(set(concepts))
    
    def extract_momentum_concepts(self) -> list:
        """Extract momentum trading concepts"""
        concepts = []
        
        sentences = re.split(r'[.!?]+', self.text)
        
        momentum_keywords = [
            'momentum', 'trend following', 'breakout', 'moving average',
            'macd', 'rsi', 'trend', 'directional', 'price acceleration',
            'trend continuation', 'crossover'
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20 or len(sentence) > 500:
                continue
                
            sentence_lower = sentence.lower()
            if any(keyword in sentence_lower for keyword in momentum_keywords):
                concepts.append(sentence)
        
        return list(set(concepts))
    
    def extract_key_examples(self) -> list:
        """Extract practical examples from the book"""
        examples = []
        
        # Look for example sections
        example_pattern = r'Example\s+\d+\.\d+[^=]+'
        matches = re.findall(example_pattern, self.text, re.DOTALL)
        
        for match in matches:
            # Clean up the example
            cleaned = re.sub(r'\s+', ' ', match).strip()
            if len(cleaned) > 50:
                examples.append(cleaned[:1000])  # Limit length
        
        return examples
    
    def create_comprehensive_extraction(self):
        """Create comprehensive knowledge extraction files"""
        print("Extracting comprehensive trading knowledge...")
        
        # Extract all categories
        extractions = {
            "formulas_and_equations": self.extract_formulas_and_equations(),
            "trading_rules": self.extract_trading_rules(),
            "risk_management": self.extract_risk_management_concepts(),
            "backtesting_principles": self.extract_backtesting_principles(),
            "performance_metrics": self.extract_performance_metrics(),
            "mean_reversion": self.extract_mean_reversion_concepts(),
            "momentum_trading": self.extract_momentum_concepts(),
            "practical_examples": self.extract_key_examples(),
        }
        
        # Save individual category files
        for category, items in extractions.items():
            if items:
                file_path = self.output_dir / f"{category}.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {category.replace('_', ' ').title()}\n")
                    f.write(f"Extracted from: Quantitative Trading by Ernie Chan\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for i, item in enumerate(items, 1):
                        f.write(f"## {category.replace('_', ' ').title()} #{i}\n\n")
                        f.write(item)
                        f.write("\n\n" + "-" * 40 + "\n\n")
                
                print(f"Created {file_path} with {len(items)} items")
        
        # Create master knowledge file for Ollama model
        self.create_ollama_knowledge_base(extractions)
        
        return extractions
    
    def create_ollama_knowledge_base(self, extractions: dict):
        """Create consolidated knowledge base for Ollama model"""
        knowledge_file = self.output_dir / "ollama_trading_knowledge.txt"
        
        with open(knowledge_file, 'w', encoding='utf-8') as f:
            f.write("# QUANTITATIVE TRADING KNOWLEDGE BASE\n")
            f.write("# For Ollama Specialized Trading Model\n")
            f.write(f"# Source: Quantitative Trading by Ernie Chan\n")
            f.write(f"# Extracted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=" * 80 + "\n\n")
            
            # Core trading principles
            f.write("## CORE TRADING PRINCIPLES\n\n")
            f.write("### Kelly Formula and Position Sizing\n")
            f.write("- f* = m / σ² (optimal leverage)\n")
            f.write("- F* = C⁻¹M (multi-strategy allocation)\n")
            f.write("- Half-Kelly betting for safety: f/2\n")
            f.write("- Risk decreases long-term growth rate\n")
            f.write("- Continuous rebalancing required\n\n")
            
            f.write("### Risk Management Core Rules\n")
            f.write("- Reduce position size after losses\n")
            f.write("- Increase position size after profits\n")
            f.write("- Maximum drawdown limits based on historical data\n")
            f.write("- Consider fat-tail events (Black Swan)\n")
            f.write("- Stop losses only work in trending markets\n\n")
            
            # Write all extracted knowledge
            for category, items in extractions.items():
                if items and category != "practical_examples":  # Handle examples separately
                    f.write(f"## {category.replace('_', ' ').upper()}\n\n")
                    for item in items:
                        f.write(f"- {item}\n")
                    f.write("\n")
            
            # Add practical examples
            if extractions.get("practical_examples"):
                f.write("## PRACTICAL EXAMPLES\n\n")
                for i, example in enumerate(extractions["practical_examples"], 1):
                    f.write(f"### Example {i}\n")
                    f.write(example)
                    f.write("\n\n")
        
        print(f"Master knowledge base created: {knowledge_file}")
        return knowledge_file


if __name__ == "__main__":
    extractor = TradingKnowledgeExtractor()
    extractions = extractor.create_comprehensive_extraction()
    
    print(f"\nKnowledge extraction complete!")
    print(f"Categories extracted:")
    for category, items in extractions.items():
        print(f"- {category}: {len(items)} items")
    
    print(f"\nFiles created in: books/processed/trading_knowledge/")
    print("Ready for Ollama model creation with comprehensive trading knowledge!")