"""
Analizador avanzado de reportes Excel para Ollama
Extrae y analiza automáticamente todos los reportes Excel del sistema
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Any, Optional

class ExcelAnalyzer:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.analysis_cache = {}
        
    def find_all_excel_files(self) -> List[Path]:
        """Encuentra todos los archivos Excel en el proyecto"""
        excel_files = []
        
        # Rutas donde buscar Excel files
        search_paths = [
            self.project_root,
            self.project_root / "reports",
            self.project_root / "tools" / "reports",
            self.project_root / "archive",
            self.project_root / "data",
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                # Buscar archivos .xlsx y .xls
                excel_files.extend(search_path.rglob("*.xlsx"))
                excel_files.extend(search_path.rglob("*.xls"))
        
        # Filtrar y ordenar por fecha de modificación
        valid_files = []
        for file in excel_files:
            try:
                if file.stat().st_size > 0:  # Solo archivos no vacíos
                    valid_files.append(file)
            except:
                continue
        
        # Ordenar por fecha de modificación (más recientes primero)
        valid_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        return valid_files
    
    def analyze_excel_file(self, excel_path: Path) -> Dict[str, Any]:
        """Analiza completamente un archivo Excel"""
        
        analysis = {
            "filename": excel_path.name,
            "path": str(excel_path),
            "modified_date": datetime.fromtimestamp(excel_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "size_mb": round(excel_path.stat().st_size / 1024 / 1024, 2),
            "sheets": {},
            "summary": {},
            "key_insights": [],
            "data_types": [],
            "potential_trading_data": False
        }
        
        try:
            xl_file = pd.ExcelFile(excel_path)
            
            # Analizar cada hoja
            for sheet_name in xl_file.sheet_names:
                try:
                    sheet_analysis = self._analyze_sheet(xl_file, sheet_name, excel_path)
                    analysis["sheets"][sheet_name] = sheet_analysis
                    
                    # Detectar si contiene datos de trading
                    if self._is_trading_data(sheet_analysis):
                        analysis["potential_trading_data"] = True
                        
                except Exception as e:
                    analysis["sheets"][sheet_name] = {"error": str(e)}
            
            # Generar resumen general
            analysis["summary"] = self._generate_file_summary(analysis)
            analysis["key_insights"] = self._extract_key_insights(analysis)
            
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    def _analyze_sheet(self, xl_file: pd.ExcelFile, sheet_name: str, excel_path: Path) -> Dict[str, Any]:
        """Analiza una hoja específica del Excel"""
        
        try:
            # Leer la hoja (limitando filas para eficiencia)
            df = pd.read_excel(xl_file, sheet_name=sheet_name, nrows=1000)
            
            sheet_analysis = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist(),
                "data_types": df.dtypes.to_dict(),
                "numeric_columns": df.select_dtypes(include=[np.number]).columns.tolist(),
                "date_columns": df.select_dtypes(include=['datetime64']).columns.tolist(),
                "text_columns": df.select_dtypes(include=['object']).columns.tolist(),
                "null_counts": df.isnull().sum().to_dict(),
                "sample_data": [],
                "statistics": {},
                "patterns": []
            }
            
            # Obtener muestra de datos (primeras 3 filas)
            if len(df) > 0:
                sheet_analysis["sample_data"] = df.head(3).to_dict('records')
            
            # Estadísticas para columnas numéricas
            if sheet_analysis["numeric_columns"]:
                numeric_stats = df[sheet_analysis["numeric_columns"]].describe()
                sheet_analysis["statistics"] = numeric_stats.to_dict()
            
            # Detectar patrones específicos de trading
            sheet_analysis["patterns"] = self._detect_trading_patterns(df, sheet_name)
            
            return sheet_analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    def _detect_trading_patterns(self, df: pd.DataFrame, sheet_name: str) -> List[str]:
        """Detecta patrones específicos de trading en los datos"""
        patterns = []
        
        # Detectar columnas relacionadas con trading
        trading_keywords = [
            'symbol', 'ticker', 'price', 'pnl', 'profit', 'loss', 'entry', 'exit',
            'position', 'trade', 'return', 'portfolio', 'value', 'quantity',
            'buy', 'sell', 'long', 'short', 'strategy'
        ]
        
        columns_lower = [col.lower() for col in df.columns]
        
        for keyword in trading_keywords:
            matching_cols = [col for col in columns_lower if keyword in col]
            if matching_cols:
                patterns.append(f"Trading data detected: {keyword} columns found")
        
        # Detectar símbolos de acciones (patrones como AAPL, MSFT, etc.)
        for col in df.columns:
            if df[col].dtype == 'object':
                sample_values = df[col].dropna().astype(str).head(10).tolist()
                stock_symbols = [val for val in sample_values if re.match(r'^[A-Z]{1,5}$', val)]
                if stock_symbols:
                    patterns.append(f"Stock symbols detected in {col}: {stock_symbols[:3]}")
        
        # Detectar rangos de fechas típicos de reportes de trading
        date_columns = df.select_dtypes(include=['datetime64']).columns
        for col in date_columns:
            date_range = df[col].max() - df[col].min()
            if date_range.days > 7:  # Más de una semana
                patterns.append(f"Date range in {col}: {date_range.days} days")
        
        # Detectar valores monetarios
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64']:
                values = df[col].dropna()
                if len(values) > 0:
                    avg_value = abs(values.mean())
                    if 10 < avg_value < 1000000:  # Rango típico de precios de acciones/PnL
                        patterns.append(f"Potential monetary values in {col}: avg ${avg_value:.2f}")
        
        return patterns
    
    def _is_trading_data(self, sheet_analysis: Dict[str, Any]) -> bool:
        """Determina si una hoja contiene datos de trading"""
        patterns = sheet_analysis.get("patterns", [])
        return len([p for p in patterns if "Trading data detected" in p or "Stock symbols detected" in p]) > 0
    
    def _generate_file_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Genera resumen del archivo completo"""
        total_rows = sum(sheet.get("rows", 0) for sheet in analysis["sheets"].values() if isinstance(sheet, dict) and "rows" in sheet)
        total_columns = sum(sheet.get("columns", 0) for sheet in analysis["sheets"].values() if isinstance(sheet, dict) and "columns" in sheet)
        
        summary = {
            "total_sheets": len(analysis["sheets"]),
            "total_rows": total_rows,
            "total_columns": total_columns,
            "has_trading_data": analysis["potential_trading_data"],
            "file_age_days": (datetime.now() - datetime.fromtimestamp(Path(analysis["path"]).stat().st_mtime)).days
        }
        
        return summary
    
    def _extract_key_insights(self, analysis: Dict[str, Any]) -> List[str]:
        """Extrae insights clave del archivo"""
        insights = []
        
        summary = analysis["summary"]
        
        # Insights sobre el tamaño
        if summary["total_rows"] > 1000:
            insights.append(f"📊 Dataset grande: {summary['total_rows']:,} filas total")
        
        # Insights sobre trading data
        if analysis["potential_trading_data"]:
            insights.append("🎯 Contiene datos de trading identificados")
        
        # Insights sobre actualidad
        if summary["file_age_days"] < 7:
            insights.append("🕒 Archivo reciente (menos de 7 días)")
        elif summary["file_age_days"] < 30:
            insights.append("📅 Archivo del último mes")
        
        # Insights específicos por hoja
        for sheet_name, sheet_data in analysis["sheets"].items():
            if isinstance(sheet_data, dict) and "patterns" in sheet_data:
                if sheet_data["patterns"]:
                    insights.append(f"🔍 Hoja '{sheet_name}': {len(sheet_data['patterns'])} patrones detectados")
        
        return insights
    
    def generate_excel_context_for_ollama(self, max_files: int = 10) -> str:
        """Genera contexto completo de Excel files para Ollama"""
        
        print("📊 Analizando archivos Excel...")
        excel_files = self.find_all_excel_files()[:max_files]  # Limitar cantidad
        
        if not excel_files:
            return "**No se encontraron archivos Excel en el proyecto**"
        
        context = f"""
# 📈 ANÁLISIS COMPLETO DE REPORTES EXCEL

**Total de archivos encontrados:** {len(excel_files)}
**Análisis generado:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📋 RESUMEN DE ARCHIVOS ANALIZADOS

"""
        
        trading_files = []
        other_files = []
        
        for excel_file in excel_files:
            print(f"   Analizando: {excel_file.name}")
            analysis = self.analyze_excel_file(excel_file)
            
            if analysis.get("potential_trading_data", False):
                trading_files.append(analysis)
            else:
                other_files.append(analysis)
        
        # Sección de archivos de trading
        if trading_files:
            context += "\n## 🎯 ARCHIVOS CON DATOS DE TRADING\n\n"
            for analysis in trading_files:
                context += self._format_excel_analysis(analysis, detailed=True)
        
        # Sección de otros archivos
        if other_files:
            context += "\n## 📄 OTROS ARCHIVOS EXCEL\n\n"
            for analysis in other_files[:5]:  # Limitar a 5 otros archivos
                context += self._format_excel_analysis(analysis, detailed=False)
        
        # Resumen final
        context += f"""
## 📊 RESUMEN EJECUTIVO

- **Total archivos:** {len(excel_files)}
- **Con datos de trading:** {len(trading_files)}
- **Otros archivos:** {len(other_files)}
- **Archivos recientes (< 30 días):** {len([f for f in trading_files + other_files if f['summary']['file_age_days'] < 30])}

**Los archivos están disponibles para análisis detallado. Puedes preguntar sobre cualquier archivo específico o tendencias en los datos.**
"""
        
        return context
    
    def _format_excel_analysis(self, analysis: Dict[str, Any], detailed: bool = True) -> str:
        """Formatea el análisis de un archivo Excel"""
        
        formatted = f"""
### 📊 {analysis['filename']}
**Archivo:** `{Path(analysis['path']).name}`
**Modificado:** {analysis['modified_date']} ({analysis['summary']['file_age_days']} días atrás)
**Tamaño:** {analysis['size_mb']} MB

"""
        
        # Key insights
        if analysis['key_insights']:
            formatted += "**🔍 Insights clave:**\n"
            for insight in analysis['key_insights']:
                formatted += f"- {insight}\n"
            formatted += "\n"
        
        if detailed and analysis['potential_trading_data']:
            # Detalles de hojas con datos de trading
            formatted += "**📈 Hojas con datos de trading:**\n"
            for sheet_name, sheet_data in analysis['sheets'].items():
                if isinstance(sheet_data, dict) and sheet_data.get('patterns'):
                    formatted += f"\n*Hoja: {sheet_name}*\n"
                    formatted += f"- {sheet_data['rows']:,} filas, {sheet_data['columns']} columnas\n"
                    formatted += f"- Columnas numéricas: {len(sheet_data['numeric_columns'])}\n"
                    
                    if sheet_data['patterns']:
                        formatted += "- Patrones detectados:\n"
                        for pattern in sheet_data['patterns'][:3]:  # Solo primeros 3
                            formatted += f"  • {pattern}\n"
        
        else:
            # Resumen básico
            formatted += f"**Hojas:** {analysis['summary']['total_sheets']} | **Filas totales:** {analysis['summary']['total_rows']:,}\n"
        
        formatted += "\n---\n"
        return formatted
    
    def save_excel_analysis(self, output_file: str = "excel_analysis_complete.json") -> Path:
        """Guarda análisis completo en JSON"""
        
        excel_files = self.find_all_excel_files()
        complete_analysis = {
            "analysis_date": datetime.now().isoformat(),
            "total_files": len(excel_files),
            "files": []
        }
        
        for excel_file in excel_files:
            analysis = self.analyze_excel_file(excel_file)
            complete_analysis["files"].append(analysis)
        
        output_path = self.project_root / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(complete_analysis, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"💾 Análisis completo guardado en: {output_file}")
        return output_path

if __name__ == "__main__":
    analyzer = ExcelAnalyzer()
    
    print("📊 ANALIZADOR DE REPORTES EXCEL PARA OLLAMA")
    print("=" * 50)
    
    # Generar contexto
    context = analyzer.generate_excel_context_for_ollama()
    
    # Guardar contexto
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    context_file = f"ollama_excel_context_{timestamp}.txt"
    
    with open(analyzer.project_root / context_file, 'w', encoding='utf-8') as f:
        f.write(context)
    
    print(f"\n✅ Contexto Excel guardado en: {context_file}")
    print(f"📏 Tamaño: {len(context):,} caracteres")
    
    # Intentar copiar al clipboard
    try:
        import pyperclip
        pyperclip.copy(context)
        print("📋 Contexto copiado al clipboard!")
    except ImportError:
        print("⚠️ Para auto-copy instala: pip install pyperclip")
    
    # Guardar análisis detallado
    analyzer.save_excel_analysis()