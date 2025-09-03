"""
Sistema avanzado para extraer TODO el conocimiento del código
para que Ollama tenga el mismo contexto que Claude Code
"""

import os
import ast
import json
import pandas as pd
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
import sqlite3
import re

@dataclass
class StrategyInfo:
    name: str
    file_path: str
    description: str
    methods: List[str]
    parameters: Dict[str, Any]
    risk_management: Dict[str, Any]
    entry_conditions: List[str]
    exit_conditions: List[str]

@dataclass
class ServiceInfo:
    name: str
    file_path: str
    description: str
    key_methods: List[str]
    dependencies: List[str]
    config_params: Dict[str, Any]

@dataclass
class DatabaseSchema:
    table_name: str
    columns: List[Dict[str, str]]
    relationships: List[str]
    purpose: str

class CodeKnowledgeExtractor:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.knowledge_base = {
            "strategies": [],
            "services": [],
            "database_schema": [],
            "api_endpoints": [],
            "trading_logic": {},
            "risk_management": {},
            "configuration": {},
            "file_structure": {},
            "recent_reports": []
        }
    
    def extract_strategies(self):
        """Extrae información de todas las estrategias de trading"""
        strategies_path = self.project_root / "src" / "traders" / "strategies"
        
        if not strategies_path.exists():
            return []
        
        strategies = []
        for py_file in strategies_path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
                
            strategy_info = self._analyze_strategy_file(py_file)
            if strategy_info:
                strategies.append(strategy_info)
        
        return strategies
    
    def _analyze_strategy_file(self, file_path: Path) -> Optional[StrategyInfo]:
        """Analiza un archivo de estrategia específico"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            strategy_name = file_path.stem
            methods = []
            entry_conditions = []
            exit_conditions = []
            parameters = {}
            risk_management = {}
            
            # Buscar clases de estrategia
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if "Strategy" in node.name:
                        strategy_name = node.name
                        
                        # Extraer métodos
                        for item in node.body:
                            if isinstance(item, ast.FunctionDef):
                                methods.append(item.name)
                                
                                # Buscar condiciones de entrada/salida
                                if "entry" in item.name.lower() or "buy" in item.name.lower():
                                    entry_conditions.append(f"Method: {item.name}")
                                elif "exit" in item.name.lower() or "sell" in item.name.lower():
                                    exit_conditions.append(f"Method: {item.name}")
                
                # Buscar configuraciones
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if "config" in target.id.lower() or "param" in target.id.lower():
                                try:
                                    value = ast.literal_eval(node.value)
                                    parameters[target.id] = value
                                except:
                                    parameters[target.id] = "Complex expression"
            
            # Buscar patrones de risk management en el código
            risk_patterns = re.findall(r'stop_loss.*?=.*?([0-9.]+)', content, re.IGNORECASE)
            take_profit_patterns = re.findall(r'take_profit.*?=.*?([0-9.]+)', content, re.IGNORECASE)
            
            if risk_patterns:
                risk_management["stop_loss_levels"] = risk_patterns
            if take_profit_patterns:
                risk_management["take_profit_levels"] = take_profit_patterns
            
            # Extraer descripción del docstring
            description = "No description available"
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and "Strategy" in node.name:
                    if ast.get_docstring(node):
                        description = ast.get_docstring(node)
                        break
            
            return StrategyInfo(
                name=strategy_name,
                file_path=str(file_path.relative_to(self.project_root)),
                description=description,
                methods=methods,
                parameters=parameters,
                risk_management=risk_management,
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions
            )
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return None
    
    def extract_services(self):
        """Extrae información de todos los servicios"""
        services_path = self.project_root / "src" / "api" / "services"
        services = []
        
        if services_path.exists():
            for py_file in services_path.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                service_info = self._analyze_service_file(py_file)
                if service_info:
                    services.append(service_info)
        
        return services
    
    def _analyze_service_file(self, file_path: Path) -> Optional[ServiceInfo]:
        """Analiza un archivo de servicio específico"""
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            
            service_name = file_path.stem
            key_methods = []
            dependencies = []
            config_params = {}
            
            # Extraer imports (dependencias)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
            
            # Extraer clases y métodos principales
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            if not item.name.startswith('_'):  # Solo métodos públicos
                                key_methods.append(item.name)
            
            description = f"Service: {service_name}"
            
            return ServiceInfo(
                name=service_name,
                file_path=str(file_path.relative_to(self.project_root)),
                description=description,
                key_methods=key_methods,
                dependencies=list(set(dependencies)),
                config_params=config_params
            )
            
        except Exception as e:
            print(f"Error analyzing service {file_path}: {e}")
            return None
    
    def extract_database_schema(self):
        """Extrae el esquema completo de la base de datos"""
        db_path = self.project_root / "trading.db"
        schemas = []
        
        if not db_path.exists():
            return schemas
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Obtener todas las tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                # Obtener esquema de cada tabla
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns_info = cursor.fetchall()
                
                columns = []
                for col_info in columns_info:
                    columns.append({
                        "name": col_info[1],
                        "type": col_info[2],
                        "not_null": bool(col_info[3]),
                        "primary_key": bool(col_info[5])
                    })
                
                # Determinar propósito basado en el nombre
                purpose = self._determine_table_purpose(table_name)
                
                schemas.append(DatabaseSchema(
                    table_name=table_name,
                    columns=columns,
                    relationships=[],  # TODO: Extraer foreign keys
                    purpose=purpose
                ))
            
            conn.close()
            
        except Exception as e:
            print(f"Error extracting database schema: {e}")
        
        return schemas
    
    def _determine_table_purpose(self, table_name: str) -> str:
        """Determina el propósito de una tabla basado en su nombre"""
        purposes = {
            "positions": "Almacena todas las posiciones de trading (LONG/SHORT)",
            "transactions": "Registra todas las transacciones realizadas",
            "portfolio_state": "Estado actual del portfolio",
            "symbols": "Símbolos monitoreados y sus scores",
            "stocks": "Información de stocks del watchlist",
            "crypto": "Información de criptomonedas",
            "strategy_config": "Configuración de estrategias de trading"
        }
        return purposes.get(table_name, f"Tabla: {table_name}")
    
    def extract_recent_reports(self):
        """Extrae información de los reportes Excel más recientes"""
        reports = []
        
        # Buscar archivos Excel en diferentes ubicaciones
        search_paths = [
            self.project_root / "reports",
            self.project_root / "tools" / "reports", 
            self.project_root,  # Archivos en root
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                for excel_file in search_path.glob("*.xlsx"):
                    try:
                        # Leer metadata del Excel
                        xl_file = pd.ExcelFile(excel_file)
                        
                        report_info = {
                            "filename": excel_file.name,
                            "path": str(excel_file),
                            "sheets": xl_file.sheet_names,
                            "modified": excel_file.stat().st_mtime,
                            "summary": self._analyze_excel_content(excel_file)
                        }
                        reports.append(report_info)
                        
                    except Exception as e:
                        print(f"Error analyzing Excel {excel_file}: {e}")
        
        # Ordenar por fecha de modificación (más recientes primero)
        reports.sort(key=lambda x: x["modified"], reverse=True)
        return reports[:10]  # Solo los 10 más recientes
    
    def _analyze_excel_content(self, excel_path: Path) -> Dict[str, Any]:
        """Analiza el contenido de un archivo Excel"""
        try:
            xl_file = pd.ExcelFile(excel_path)
            summary = {"sheets_summary": {}}
            
            for sheet_name in xl_file.sheet_names[:3]:  # Solo primeras 3 hojas
                df = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=100)
                
                sheet_summary = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
                    "sample_data": df.head(3).to_dict('records') if len(df) > 0 else []
                }
                summary["sheets_summary"][sheet_name] = sheet_summary
            
            return summary
            
        except Exception as e:
            return {"error": str(e)}
    
    def extract_api_endpoints(self):
        """Extrae información de todos los endpoints de la API"""
        api_path = self.project_root / "src" / "api" / "routers"
        endpoints = []
        
        if api_path.exists():
            for py_file in api_path.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue
                
                content = py_file.read_text(encoding='utf-8')
                
                # Buscar decoradores de FastAPI
                endpoint_patterns = [
                    r'@router\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']',
                    r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
                ]
                
                for pattern in endpoint_patterns:
                    matches = re.findall(pattern, content)
                    for method, path in matches:
                        endpoints.append({
                            "method": method.upper(),
                            "path": path,
                            "file": str(py_file.relative_to(self.project_root))
                        })
        
        return endpoints
    
    def generate_complete_knowledge_base(self):
        """Genera la base de conocimiento completa"""
        print("🔍 Extrayendo conocimiento completo del código...")
        
        # Extraer toda la información
        self.knowledge_base["strategies"] = [asdict(s) for s in self.extract_strategies()]
        self.knowledge_base["services"] = [asdict(s) for s in self.extract_services()]
        self.knowledge_base["database_schema"] = [asdict(s) for s in self.extract_database_schema()]
        self.knowledge_base["api_endpoints"] = self.extract_api_endpoints()
        self.knowledge_base["recent_reports"] = self.extract_recent_reports()
        
        # Generar estructura de archivos
        self.knowledge_base["file_structure"] = self._generate_file_structure()
        
        # Configuración del sistema
        self.knowledge_base["configuration"] = self._extract_system_config()
        
        return self.knowledge_base
    
    def _generate_file_structure(self) -> Dict[str, Any]:
        """Genera un mapa de la estructura de archivos"""
        structure = {}
        
        key_directories = [
            "src/api",
            "src/traders", 
            "src/core",
            "src/utils",
            "tools",
            "local_ai"
        ]
        
        for dir_path in key_directories:
            full_path = self.project_root / dir_path
            if full_path.exists():
                structure[dir_path] = self._scan_directory(full_path)
        
        return structure
    
    def _scan_directory(self, directory: Path, max_depth: int = 2) -> Dict[str, Any]:
        """Escanea un directorio hasta cierta profundidad"""
        if max_depth <= 0:
            return {}
        
        result = {"files": [], "subdirs": {}}
        
        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix in ['.py', '.md', '.json', '.yaml', '.yml']:
                    result["files"].append(item.name)
                elif item.is_dir() and not item.name.startswith('.'):
                    result["subdirs"][item.name] = self._scan_directory(item, max_depth - 1)
        except PermissionError:
            pass
        
        return result
    
    def _extract_system_config(self) -> Dict[str, Any]:
        """Extrae configuración del sistema"""
        config = {}
        
        # Leer CLAUDE.md si existe
        claude_md = self.project_root / "CLAUDE.md"
        if claude_md.exists():
            config["project_instructions"] = claude_md.read_text(encoding='utf-8')
        
        # Leer requirements.txt
        requirements = self.project_root / "requirements.txt"
        if requirements.exists():
            config["dependencies"] = requirements.read_text(encoding='utf-8').split('\n')
        
        return config
    
    def save_knowledge_base(self, output_file: str = "ollama_complete_knowledge.json"):
        """Guarda la base de conocimiento en un archivo JSON"""
        output_path = self.project_root / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📁 Base de conocimiento guardada en: {output_file}")
        return output_path

if __name__ == "__main__":
    extractor = CodeKnowledgeExtractor()
    knowledge_base = extractor.generate_complete_knowledge_base()
    
    print("\n" + "="*60)
    print("RESUMEN DE CONOCIMIENTO EXTRAÍDO:")
    print("="*60)
    print(f"📊 Estrategias encontradas: {len(knowledge_base['strategies'])}")
    print(f"🔧 Servicios encontrados: {len(knowledge_base['services'])}")  
    print(f"🗄️  Tablas de BD: {len(knowledge_base['database_schema'])}")
    print(f"🌐 API Endpoints: {len(knowledge_base['api_endpoints'])}")
    print(f"📈 Reportes recientes: {len(knowledge_base['recent_reports'])}")
    
    # Guardar todo
    output_file = extractor.save_knowledge_base()
    print(f"\n✅ Conocimiento completo disponible para Ollama!")