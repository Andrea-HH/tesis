"""Reproduce09 desde insumos existentes; no reconstruye integración ni exporta texto."""
from tesis_enasem.central_analysis import analyze,validate
from tesis_enasem.central_supplement import analyze as supplement
if __name__=='__main__':
    analyze()
    result=supplement()
    validate(result)
    print('Contraste09 validado. Exportar con python scripts/export_central_analysis.py')
