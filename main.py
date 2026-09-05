"""
Enterprise Compliance Intelligence Platform — CLI Entry Point

Usage:
  python main.py -i data/input/report.pdf          # build knowledge graph
  python main.py -q "What are the key risks?"      # query
  python main.py -s                                 # start visualization server
"""
import argparse
import asyncio
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from backend.builder import MMKGBuilder
from backend.retrieval.query import GraphRAGQuery
from backend.visualization.server import run_visualization_server
from backend.config import settings as parameter


def parse_args():
    p = argparse.ArgumentParser(description="Enterprise Compliance Intelligence Platform")
    p.add_argument("-i", "--input",       help="File path to index (.pdf, .docx, .xlsx, .mp3, .wav, .png, ...)")
    p.add_argument("-q", "--query",       help="Query the knowledge graph")
    p.add_argument("-s", "--serve",       action="store_true", help="Start visualization server")
    p.add_argument("-w", "--working-dir", help="Working directory override")
    p.add_argument("-o", "--output-dir",  help="Output directory override")
    p.add_argument("-m", "--mmkg-name",   help="Knowledge graph name override")
    p.add_argument("-f", "--force",       action="store_true", help="Force rebuild (ignore cache)")
    p.add_argument("-v", "--verbose",     action="store_true", help="Verbose logging")
    p.add_argument("--port",              type=int, default=5000, help="Visualization server port")
    return p.parse_args()


def main():
    args = parse_args()

    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    # Apply overrides
    if args.working_dir: parameter.WORKING_DIR = args.working_dir
    if args.output_dir:  parameter.OUTPUT_DIR  = args.output_dir
    if args.mmkg_name:   parameter.MMKG_NAME   = args.mmkg_name

    if args.input:
        builder = MMKGBuilder(file_path=args.input)
        asyncio.run(builder.index(args.input))

    elif args.query:
        querier = GraphRAGQuery()
        answer  = asyncio.run(querier.query(args.query))
        print("\n" + "="*60)
        print(answer)
        print("="*60)

    elif args.serve:
        run_visualization_server(port=args.port)

    else:
        # Default: show help
        print(__doc__)


if __name__ == "__main__":
    main()
