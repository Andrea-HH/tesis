from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes
"""Ejecuta CP1 localmente. Solo exporta agregados a reports/ (ignorado)."""
from pathlib import Path
import hashlib
import json
import sys
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_path('', 'src')))
from tesis_enasem.io import load_stata
from tesis_enasem.audit import build_audit
from tesis_enasem.audit_report import plot_wave, plot_longitudinal, write_cp1_report
import matplotlib.pyplot as plt


def main() -> None:
    """Lee original sin modificar y comprueba reconciliaciones contra el diccionario."""
    source = project_path('', 'data/raw/simpleMHAS.dta')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report', action='store_true', help='Regenerar informes agregados en docs/.')
    args = parser.parse_args()
    original_hash = hashlib.sha256(read_project_bytes(source)).hexdigest()
    raw = load_stata(source)
    # Sin filtros de edad, entrevista o número de rondas: None es el predeterminado.
    tables = build_audit(raw)
    assert tables['estructura'].registros_excluidos_por_seleccion.iloc[0] == 0
    assert tables['estructura'].personas_excluidas_por_seleccion.iloc[0] == 0
    expected = [15186,14250,18465,15988,18249,17538]
    assert tables['rondas'].registros.tolist() == expected, 'Discrepancia con cuadro 1 del diccionario'
    expected_types = [[0,14154,0,1032,0], [12363,163,1134,44,546],
                      [8868,5580,959,316,2742], [13254,596,884,45,1209],
                      [11183,4603,1122,206,1135], [14336,148,1247,8,1799]]
    from tesis_enasem.audit import INTERVIEW_LABELS
    for wave, counts in enumerate(expected_types, 1):
        table = tables['demografia']
        table = table.loc[table.ronda.eq(wave) & table.variable.eq('tipent')].set_index('categoria')
        assert table.reindex(INTERVIEW_LABELS.values()).n.tolist() == counts
    miss = tables['faltantes']
    assert (miss.groupby(['ronda','variable']).n.sum() == miss.groupby(['ronda','variable']).denominador.first()).all()
    flow = tables['flujo']
    assert (flow.antes-flow.excluidos).equals(flow.despues)
    trans = tables['transiciones']
    assert (trans.continuan+trans.no_observadas).equals(trans.denominador_origen)
    assert tables['patrones'].personas.sum() == tables['estructura'].personas.iloc[0]
    age = tables['edad_grupos']
    assert age.groupby('ronda').n.sum().tolist() == expected
    assert age.groupby('ronda').categoria.nunique().eq(7).all()
    for name in ['muestras', 'muestras_ronda']:
        sample = tables[name]
        assert (sample.registros + sample.registros_excluidos).equals(sample.denominador_registros)
        assert (sample.personas + sample.personas_excluidas).equals(sample.denominador_personas)
    profiles = tables['perfiles_seguimiento']
    for wave in range(1, 6):
        profile = profiles.loc[profiles.ronda.eq(wave) & profiles.variable.eq('edad')]
        assert profile.denominador.sum() == expected[wave-1]
    checks = tables['consistencia'].set_index('control').n.to_dict()
    out = project_path('', 'reports/tables')
    out.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_json(out/f'cp1_{name}.json', orient='table', force_ascii=False, indent=2)
    meta = {'fecha': '2026-10-11', 'python': sys.executable,
            'sha256_datos': original_hash,
            'poblacion_principal': 'Toda la población registrada; sin filtros',
            'registros_originales_conservados': len(raw), 'registros_excluidos_principal': 0,
            'fuente': 'ENASEMsimple v2, enero 2025, cuadro 1 y apéndice 1',
            'reconciliaciones': 'aprobadas', 'consistencia': checks}
    write_project_text(out/'cp1_ejecucion.json', json.dumps(meta, ensure_ascii=False, indent=2))
    for wave in range(1,7):
        plt.close(plot_wave(raw, wave, project_path('', 'reports/figures')))
    plt.close(plot_longitudinal(tables, project_path('', 'reports/figures')))
    if args.write_report:
        write_cp1_report(tables, ROOT)
    assert hashlib.sha256(read_project_bytes(source)).hexdigest() == original_hash
    print(tables['estructura'].to_string(index=False))
    print(tables['muestras'].to_string(index=False))
    print(tables['transiciones'].to_string(index=False))
    print(tables['edad_grupos'].to_string(index=False))
    print(checks)
    print('Reconciliaciones aprobadas; agregados y 7 figuras en reports/.')


if __name__ == '__main__':
    main()
