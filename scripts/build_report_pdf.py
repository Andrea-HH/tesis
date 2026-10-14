"""Genera y valida el único PDF académico desde resultados/INFORME_GENERAL.md."""
import argparse
from tesis_enasem.report_pdf import generate_report_pdf, validate_report_sync

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Comprobar sincronización sin regenerar.')
    args=parser.parse_args()
    evidence = validate_report_sync() if args.check else generate_report_pdf()
    print(f"Informe {'sincronizado' if args.check else 'generado'}: {evidence['paginas']} páginas, {evidence['tablas']} cuadros, {len(evidence['figuras'])} figuras; texto y celdas cotejados.")
