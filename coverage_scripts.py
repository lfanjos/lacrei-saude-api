#!/usr/bin/env python3
"""
Scripts para Análise de Cobertura - Lacrei Saúde API
====================================================

Scripts utilitários para gerar relatórios detalhados de cobertura de testes.
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_coverage_analysis():
    """Executa análise completa de cobertura"""
    print("🔍 Executando análise de cobertura...")

    try:
        # Limpa cobertura anterior
        subprocess.run(["coverage", "erase"], check=True)
        print("✅ Cache de cobertura limpo")

        # Executa testes com cobertura
        result = subprocess.run(
            [
                "python",
                "-m",
                "pytest",
                "--cov=.",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-report=json:coverage.json",
                "--cov-config=.coveragerc",
                "--cov-branch",
            ],
            capture_output=True,
            text=True,
        )

        print("📊 Análise de cobertura concluída")
        print("\n" + "=" * 60)
        print("RELATÓRIO DE COBERTURA")
        print("=" * 60)
        print(result.stdout)

        if result.stderr:
            print("\n⚠️  Avisos:")
            print(result.stderr)

        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar análise: {e}")
        return False


def generate_coverage_summary():
    """Gera resumo executivo da cobertura"""
    try:
        # Lê dados do coverage.json
        with open("coverage.json", "r") as f:
            data = json.load(f)

        summary = data.get("totals", {})
        files = data.get("files", {})

        print("\n" + "=" * 60)
        print("RESUMO EXECUTIVO DE COBERTURA")
        print("=" * 60)
        print(f"📅 Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print(f"🗂️  Total de arquivos analisados: {len(files)}")
        print(f"📝 Linhas totais: {summary.get('num_statements', 0)}")
        print(f"✅ Linhas cobertas: {summary.get('covered_lines', 0)}")
        print(f"❌ Linhas não cobertas: {summary.get('missing_lines', 0)}")
        print(f"🌿 Branches totais: {summary.get('num_branches', 0)}")
        print(f"✅ Branches cobertos: {summary.get('covered_branches', 0)}")
        print(f"📊 Cobertura total: {summary.get('percent_covered', 0):.2f}%")

        # Análise por módulo
        modules = {}
        for filepath, file_data in files.items():
            if "/" in filepath:
                module = filepath.split("/")[0]
            else:
                module = "root"

            if module not in modules:
                modules[module] = {"files": 0, "statements": 0, "covered": 0, "missing": 0}

            modules[module]["files"] += 1
            modules[module]["statements"] += file_data.get("summary", {}).get("num_statements", 0)
            modules[module]["covered"] += file_data.get("summary", {}).get("covered_lines", 0)
            modules[module]["missing"] += file_data.get("summary", {}).get("missing_lines", 0)

        print("\n📂 COBERTURA POR MÓDULO:")
        print("-" * 60)
        for module, stats in sorted(modules.items()):
            if stats["statements"] > 0:
                coverage_pct = (stats["covered"] / stats["statements"]) * 100
                status = get_coverage_status(coverage_pct)
                print(f"{module:20} {coverage_pct:6.1f}% {status} ({stats['files']} arquivos)")

        # Arquivos com baixa cobertura
        low_coverage_files = []
        for filepath, file_data in files.items():
            file_summary = file_data.get("summary", {})
            statements = file_summary.get("num_statements", 0)
            if statements > 0:
                coverage_pct = file_summary.get("percent_covered", 0)
                if coverage_pct < 70:
                    low_coverage_files.append((filepath, coverage_pct))

        if low_coverage_files:
            print(f"\n⚠️  ARQUIVOS COM BAIXA COBERTURA (<70%):")
            print("-" * 60)
            for filepath, coverage_pct in sorted(low_coverage_files, key=lambda x: x[1]):
                print(f"{filepath:50} {coverage_pct:6.1f}%")

        # Recomendações
        total_coverage = summary.get("percent_covered", 0)
        print(f"\n🎯 ANÁLISE E RECOMENDAÇÕES:")
        print("-" * 60)

        if total_coverage >= 90:
            print("🌟 Excelente! Cobertura muito alta.")
        elif total_coverage >= 80:
            print("✅ Boa cobertura. Continue melhorando.")
        elif total_coverage >= 70:
            print("⚠️  Cobertura moderada. Foque nos arquivos com baixa cobertura.")
        else:
            print("🚨 Cobertura baixa. Priorize a criação de mais testes.")

        if low_coverage_files:
            print(f"📝 Focar em {len(low_coverage_files)} arquivos com baixa cobertura")

        missing_lines = summary.get("missing_lines", 0)
        if missing_lines > 0:
            print(f"🎯 Meta: Cobrir {missing_lines} linhas adicionais")

        return True

    except FileNotFoundError:
        print("❌ Arquivo coverage.json não encontrado. Execute os testes primeiro.")
        return False
    except Exception as e:
        print(f"❌ Erro ao gerar resumo: {e}")
        return False


def get_coverage_status(coverage_pct):
    """Retorna emoji de status baseado na cobertura"""
    if coverage_pct >= 90:
        return "🌟"
    elif coverage_pct >= 80:
        return "✅"
    elif coverage_pct >= 70:
        return "⚠️"
    else:
        return "🚨"


def generate_coverage_badge():
    """Gera badge de cobertura em formato SVG"""
    try:
        with open("coverage.json", "r") as f:
            data = json.load(f)

        coverage_pct = data.get("totals", {}).get("percent_covered", 0)

        # Cores baseadas na cobertura
        if coverage_pct >= 90:
            color = "brightgreen"
        elif coverage_pct >= 80:
            color = "green"
        elif coverage_pct >= 70:
            color = "yellow"
        elif coverage_pct >= 60:
            color = "orange"
        else:
            color = "red"

        # SVG do badge
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="104" height="20">
<linearGradient id="b" x2="0" y2="100%">
<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
<stop offset="1" stop-opacity=".1"/>
</linearGradient>
<clipPath id="a">
<rect width="104" height="20" rx="3" fill="#fff"/>
</clipPath>
<g clip-path="url(#a)">
<path fill="#555" d="M0 0h63v20H0z"/>
<path fill="{color}" d="M63 0h41v20H63z"/>
<path fill="url(#b)" d="M0 0h104v20H0z"/>
</g>
<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="110">
<text x="325" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="530">coverage</text>
<text x="325" y="140" transform="scale(.1)" textLength="530">coverage</text>
<text x="825" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="310">{coverage_pct:.0f}%</text>
<text x="825" y="140" transform="scale(.1)" textLength="310">{coverage_pct:.0f}%</text>
</g>
</svg>"""

        with open("coverage-badge.svg", "w") as f:
            f.write(svg_content)

        print(f"🏆 Badge de cobertura gerado: {coverage_pct:.1f}% ({color})")
        return True

    except Exception as e:
        print(f"❌ Erro ao gerar badge: {e}")
        return False


def open_coverage_report():
    """Abre o relatório HTML de cobertura"""
    html_report = Path("htmlcov/index.html")

    if html_report.exists():
        print("🌐 Abrindo relatório HTML de cobertura...")

        import webbrowser

        webbrowser.open(f"file://{html_report.absolute()}")
        print(f"📊 Relatório disponível em: {html_report.absolute()}")
    else:
        print("❌ Relatório HTML não encontrado. Execute a análise primeiro.")


def check_coverage_requirements():
    """Verifica se a cobertura atende aos requisitos mínimos"""
    try:
        with open("coverage.json", "r") as f:
            data = json.load(f)

        coverage_pct = data.get("totals", {}).get("percent_covered", 0)

        # Requisitos mínimos
        requirements = {"minimum_total": 80, "recommended_total": 85, "excellent_total": 90}

        print(f"\n🎯 VERIFICAÇÃO DE REQUISITOS:")
        print("-" * 60)
        print(f"Cobertura atual: {coverage_pct:.2f}%")

        if coverage_pct >= requirements["excellent_total"]:
            print("🌟 EXCELENTE: Cobertura excepcional!")
            return True
        elif coverage_pct >= requirements["recommended_total"]:
            print("✅ BOM: Cobertura recomendada atingida")
            return True
        elif coverage_pct >= requirements["minimum_total"]:
            print("⚠️  MÍNIMO: Cobertura mínima atingida")
            return True
        else:
            gap = requirements["minimum_total"] - coverage_pct
            print(f"🚨 INSUFICIENTE: Faltam {gap:.2f}% para atingir o mínimo")
            return False

    except Exception as e:
        print(f"❌ Erro ao verificar requisitos: {e}")
        return False


def main():
    """Função principal do script"""
    print("🧪 LACREI SAÚDE API - ANÁLISE DE COBERTURA")
    print("=" * 60)

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "run":
            run_coverage_analysis()
            generate_coverage_summary()
        elif command == "summary":
            generate_coverage_summary()
        elif command == "badge":
            generate_coverage_badge()
        elif command == "open":
            open_coverage_report()
        elif command == "check":
            check_coverage_requirements()
        else:
            print("Comandos disponíveis:")
            print("  run     - Executa análise completa")
            print("  summary - Gera resumo executivo")
            print("  badge   - Gera badge SVG")
            print("  open    - Abre relatório HTML")
            print("  check   - Verifica requisitos")
    else:
        # Execução completa por padrão
        if run_coverage_analysis():
            generate_coverage_summary()
            generate_coverage_badge()
            check_coverage_requirements()

            print(f"\n📁 Arquivos gerados:")
            print("  • htmlcov/index.html - Relatório HTML")
            print("  • coverage.xml - Relatório XML")
            print("  • coverage.json - Dados em JSON")
            print("  • coverage-badge.svg - Badge de cobertura")


if __name__ == "__main__":
    main()
