"""Exporta agregados de titularidad, nunca microdatos, a LaTeX y BrBG."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tesis_enasem.manuscript import render_latex_table, latex_number

ROOT = Path(__file__).resolve().parents[1]


def export() -> None:
    """Selecciona una tabla/figura académica, conserva resultados exhaustivos externos."""
    report = json.loads(read_project_text(project_path('', 'docs/integracion/titularidad/resultados.json')))
    rows = [{"Año":str(r['ano']),"N personas":r['N_personas'],"Propia K":r['N_pension_propia_si'],
             "Pareja K":r['N_pension_conyuge_si'],"Titular ND":r['N_titular_indeterminado'],
             "Hogares K":r['N_hogares_pension_si']} for r in report['resumen_rondas']]
    out = project_path('', 'manuscrito/tablas')
    write_project_text(out/'titularidad_rondas.tex', render_latex_table(pd.DataFrame(rows),
        'Auditoría provisional de titularidad pensionaria en seis rondas','tab:titularidad-rondas',
        'Propia y pareja: personas de cada ronda; categorías que pueden coexistir. Titular ND: orientación indeterminada, distinta de recepción desconocida. Hogares K: entrevistas económicas únicas con recepción declarada. N hogares y estados completos en notebook 05c. En 2001 se conserva orientación del proveedor sin J1 original: comprobación independiente pendiente. K no incluye todos los apoyos públicos. Sin ponderar.',column_format='lrrrrr'))
    dup = [{"Año":str(r['ano']),"Slots":r['N_slots_declarados_enlazados'],"Con monto":r['N_slots_monto_observado'],
            "Réplicas":r['N_replicas_evitable_persona'],"Firmas iguales":r['N_firmas_coincidentes_a_revisar']}
           for r in report['duplicacion_montos']]
    write_project_text(out/'titularidad_duplicacion.tex', render_latex_table(pd.DataFrame(dup),
        'Eventos pensionarios originales y riesgo de replicación por persona','tab:titularidad-duplicacion',
        'Unidad: slot original por hogar, rama beneficiaria y contingencia. Réplicas evitables al sumar desde filas persona-ronda, no pagos duplicados comprobados. Firmas iguales requieren revisión; no se eliminan pensiones distintas por compartir importe. Los montos imputados y construidos no se suman con los originales.',column_format='lrrrr'))
    changes = sum(r['N'] for r in report['transiciones_2021'] if r['comparacion']=='clasificacion_almacenada_vs_auditada' and r['antes'] != r['despues'])
    potential = sum(r['N'] for r in report['transiciones_2021'] if r['comparacion'].startswith('contrafactual') and r['antes']=='si' and r['despues']=='no')
    partner_changes=sum(r['N'] for r in report['transiciones_2021'] if r['comparacion'].startswith('pareja_sin') and r['antes']!=r['despues'])
    partner_positives=sum(r['N'] for r in report['transiciones_2021'] if r['comparacion'].startswith('pareja_sin') and r['antes']=='si' and r['despues']=='desconocido')
    last=report['resumen_rondas'][-1]
    write_project_text(out/'titularidad_cifras.tex', '% Generado desde auditoría agregada, no editar cifras.\n'+
        f'\\newcommand{{\\titCambios}}{{{latex_number(changes)}}}\n'+
        f'\\newcommand{{\\titFalsosPropios}}{{{latex_number(potential)}}}\n'+
        f'\\newcommand{{\\titParejaSi}}{{{latex_number(last["N_pension_conyuge_si"])}}}\n'+
        f'\\newcommand{{\\titAmbos}}{{{latex_number(last["N_ambas_reciben"])}}}\n'+
        f'\\newcommand{{\\titParejaCambios}}{{{latex_number(partner_changes)}}}\n'+
        f'\\newcommand{{\\titParejaPosND}}{{{latex_number(partner_positives)}}}\n')
    fig, axes = plt.subplots(1,2,figsize=(9,5.2),gridspec_kw={'width_ratios':[1.5,1]})
    values = report['resumen_rondas']; x=np.arange(6); cmap=plt.get_cmap('BrBG')
    for shift,field,label,color in [(-.18,'N_pension_propia_si','Propia K',cmap(.1)),(.18,'N_pension_conyuge_si','De la pareja K',cmap(.9))]:
        nums=[r[field] for r in values]
        bars=axes[0].bar(x+shift,nums,width=.35,color=color,label=label)
        axes[0].bar_label(bars,fontsize=11,padding=2)
    axes[0].set_xticks(x,[str(r['ano']) for r in values]);axes[0].set_ylabel('Personas de la ronda',fontsize=12);axes[0].legend(fontsize=10)
    axes[0].set_ylim(0,max(r['N_pension_propia_si'] for r in values)*1.2)
    axes[0].set_title('Recepción K por beneficiario',fontsize=12)
    counts=[r['N_titular_indeterminado'] for r in values]
    bars=axes[1].bar(x,counts,color=[cmap(v) for v in [.08,.25,.4,.6,.75,.92]])
    axes[1].bar_label(bars,fontsize=11,padding=2)
    axes[1].set_xticks(x,[str(r['ano']) for r in values]);axes[1].set_title('Titular propio indeterminado',fontsize=12)
    axes[1].set_ylim(0,max(counts)*1.2)
    for ax in axes:
        ax.tick_params(labelsize=11)
    fig.text(.02,.015,'Sin ponderar; categorías solapadas e instrumentos distintos. 2001: proveedor, J1 pendiente.\nN personas: '+', '.join(f"{r['ano']}: {r['N_personas']:,}" for r in values[:3])+ '\n'+', '.join(f"{r['ano']}: {r['N_personas']:,}" for r in values[3:]),fontsize=9)
    fig.tight_layout(rect=(0,.15,1,1))
    path=project_path('', 'manuscrito/figuras/borradores/titularidad_rondas.png');fig.savefig(path,dpi=180);plt.close(fig)
    print('Titularidad: dos tablas, cifras y una figura BrBG exportadas desde agregados.')


if __name__ == '__main__':
    export()
