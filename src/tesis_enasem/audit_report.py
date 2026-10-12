"""Narrativa y figuras agregadas de CP1; nunca muestran identificadores."""
from __future__ import annotations

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

from .audit import frequency_table
from .config import ROUND_TO_YEAR
from .missing import numeric_enasem

WAVE_COLORS = {w: plt.cm.BrBG(x) for w, x in zip(ROUND_TO_YEAR, [.08, .25, .4, .6, .75, .92])}


def markdown_table(table: pd.DataFrame) -> str:
    """Tabla Markdown sin dependencia adicional; NaN significa no estimable."""
    def fmt(value: object) -> str:
        if pd.isna(value):
            return '—'
        if isinstance(value, float):
            return f'{value:.2f}'
        return str(value).replace('|', '/')
    header = '| ' + ' | '.join(map(str, table.columns)) + ' |'
    rule = '| ' + ' | '.join(['---'] * len(table.columns)) + ' |'
    rows = ['| ' + ' | '.join(fmt(v) for v in row) + ' |' for row in table.itertuples(index=False, name=None)]
    return '\n'.join([header, rule, *rows])


def wave_interpretation(tables: dict[str, pd.DataFrame], wave: int) -> str:
    """Interpretación calculada por ola, con denominadores y cautelas."""
    r = tables['rondas'].set_index('ronda').loc[wave]
    a = tables['edad'].set_index('ronda').loc[wave]
    e = tables['entradas'].set_index('ronda').loc[wave]
    d = tables['demografia']
    types = d.loc[d.ronda.eq(wave) & d.variable.eq('tipent')].set_index('categoria')['n']
    direct = int(types.get('Directa de seguimiento', 0) + types.get('Directa de nueva persona', 0))
    proxy = int(types.get('Sustituto de seguimiento', 0) + types.get('Sustituto de nueva persona', 0))
    death = int(types.get('Sobre fallecido', 0))
    flow = tables['flujo'].loc[tables['flujo'].ronda.eq(wave)]
    eligible = int(flow.iloc[-1]['despues'])
    total = int(r['registros'])
    demo_text = ''
    for variable, category, label in [('sexo', 'Mujer', 'mujeres'), ('est_conyugal', 'Viudo', 'personas viudas'),
                                      ('urbano', '100 mil residentes o más', 'registros en localidades de 100 mil o más habitantes')]:
        n = int(d.loc[d.ronda.eq(wave) & d.variable.eq(variable) & d.categoria.eq(category), 'n'].sum())
        demo_text += f' Se registran {n:,} {label} ({100*n/total:.2f}% del total de la ronda). '
    comparison = ''
    if wave > 1:
        previous = tables['edad'].set_index('ronda').loc[wave-1, 'mediana']
        comparison = f' La mediana de edad cambia {a["mediana"]-previous:+.1f} años respecto a la ronda anterior; es una comparación de muestras observadas, no un cambio individual. '
    return (f"La ronda {wave} ({ROUND_TO_YEAR[wave]}) contiene {total:,} registros de {int(r['personas']):,} personas. "
            f"Las entrevistas directas suman {direct:,} ({100*direct/total:.2f}% del total de la ronda), "
            f"las de sustituto {proxy:,} ({100*proxy/total:.2f}%) y las de fallecimiento {death:,} "
            f"({100*death/total:.2f}%). La primera aparición se registra para {int(e['primera_aparicion']):,} "
            f"personas; {int(e['ya_observadas']):,} ya habían sido observadas y "
            f"{int(e['reaparecen_tras_ausencia']):,} reaparecen tras faltar a la ronda inmediatamente anterior. "
            "Primera aparición y entrevista de nueva persona son conceptos distintos y se calculan por separado.\n\n"
            f"La edad es válida en {int(a['n_validos']):,}/{total:,} registros: la mediana es {a['mediana']:.1f} años "
            f"y el intervalo intercuartílico {a['q25']:.1f}–{a['q75']:.1f}. "
            f"Se observan {int(r['menores_60']):,} registros menores de 60, {int(r['edad_60_mas']):,} "
            f"de 60 o más y {int(r['edad_faltante']):,} sin edad válida. El filtro directo 60+ conserva "
            f"{eligible:,}/{total:,} ({100*eligible/total:.2f}%) y excluye {total-eligible:,}. "
            "Las tablas de flujo distinguen entrevista, edad ausente y edad insuficiente.\n\n"
            + demo_text + comparison + "\n\n"
            "Las distribuciones demográficas incluyen códigos especiales en el denominador total; la edad continua "
            "se resume únicamente entre valores válidos. Las diferencias entre rondas combinan envejecimiento, "
            "incorporaciones y selección por observación. No identifican cambios dentro de la misma persona ni "
            "efectos causales. Las entrevistas sobre fallecidos forman parte del seguimiento amplio y no son "
            "predictores directos contemporáneos. La tabla de pesos verifica disponibilidad, sin convertir "
            "su suma en un tamaño de muestra ni estimar todavía estadísticas poblacionales.")


def plot_wave(raw: pd.DataFrame, wave: int, directory: Path | None = None) -> plt.Figure:
    """Ficha con frecuencias demográficas y distribución de edad, N explícitos."""
    group = raw.loc[raw.ronda.eq(wave)]
    fig, axes = plt.subplots(2, 3, figsize=(18, 10), layout='constrained')
    for ax, variable, title in zip(axes.flat, ['tipent', 'sexo', 'est_conyugal', 'urbano', 'edad_gru'],
                                   ['Tipo de entrevista', 'Sexo', 'Estado conyugal', 'Tamaño de localidad', 'Grupos de edad']):
        tab = frequency_table(group[variable], variable).sort_values('n')
        ax.barh(tab.categoria, tab.n, color=WAVE_COLORS[wave])
        ax.bar_label(ax.containers[0], padding=3, fontsize=9)
        ax.set_xlim(0, max(tab.n)*1.24)
        ax.set_title(title)
        ax.set_xlabel(f'Frecuencia absoluta (denominador: {len(group):,})')
    age = numeric_enasem(group.edad).dropna()
    axes.flat[-1].hist(age, bins=range(10, 121, 5), color=WAVE_COLORS[wave], edgecolor='white')
    axes.flat[-1].set(xlabel='Edad en años cumplidos', ylabel='Registros por intervalo de 5 años',
                      title=f'Edad válida: n={len(age):,}; faltantes={len(group)-len(age):,}')
    fig.suptitle(f'Ronda {wave} ({ROUND_TO_YEAR[wave]}), n={len(group):,} persona-ronda', fontsize=17)
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / f'cp1_ronda_{wave}.png', dpi=150)
    return fig


def plot_longitudinal(tables: dict[str, pd.DataFrame], directory: Path | None = None) -> plt.Figure:
    """Gráficas de participación e intersecciones de personas, sin claves."""
    fig, axes = plt.subplots(1, 3, figsize=(18, 6), layout='constrained')
    t = tables['numero_rondas']
    axes[0].bar(t.rondas_observadas, t.personas, color=[WAVE_COLORS[w] for w in ROUND_TO_YEAR])
    axes[0].bar_label(axes[0].containers[0])
    axes[0].set(xlabel='Número de rondas observadas', ylabel='Personas únicas', title='Participación (incluye fallecimiento)')
    p = tables['patrones'].head(12).sort_values('personas')
    axes[1].barh(p.patron_2001_a_2021, p.personas, color=plt.cm.BrBG_r(.3))
    axes[1].bar_label(axes[1].containers[0])
    axes[1].set(xlabel='Personas únicas', title='12 patrones más frecuentes; 1=observada')
    axes[1].set_xlim(0, p.personas.max()*1.22)
    m = tables['intersecciones'].set_index('ronda')
    heatmap = axes[2].imshow(m, cmap='BrBG')
    labels = [f'R{w}\n{y}' for w, y in ROUND_TO_YEAR.items()]
    axes[2].set(xticks=range(6), yticks=range(6), xticklabels=labels, yticklabels=labels,
                title='Personas presentes en ambas rondas')
    for i in range(6):
        for j in range(6):
            rgba = heatmap.cmap(heatmap.norm(m.iloc[i,j]))
            luminance = .299*rgba[0] + .587*rgba[1] + .114*rgba[2]
            axes[2].text(j, i, f'{m.iloc[i,j]:,}', ha='center', va='center', fontsize=9,
                         color='white' if luminance < .5 else 'black')
    if directory is not None:
        directory.mkdir(parents=True, exist_ok=True)
        fig.savefig(directory / 'cp1_participacion.png', dpi=150)
    return fig


def followup_interpretation(tables: dict[str, pd.DataFrame]) -> str:
    """Compara perfiles calculados y magnitud de la selección por continuidad."""
    profile = tables['perfiles_seguimiento']
    lines = []
    for wave in range(1, 6):
        sub = profile.loc[profile.ronda.eq(wave) & profile.variable.eq('edad')].set_index('grupo')
        retained = sub.loc['Observada siguiente']
        absent = sub.loc['No observada siguiente']
        lines.append(f"En R{wave} ({ROUND_TO_YEAR[wave]}), entre vivos en origen, la edad media es "
                     f"{retained['media']:.2f} años entre quienes se observan en la ronda siguiente "
                     f"(N válido={int(retained['n']):,}/{int(retained['denominador']):,}) y "
                     f"{absent['media']:.2f} entre quienes no se observan "
                     f"(N válido={int(absent['n']):,}/{int(absent['denominador']):,}). "
                     f"La diferencia observada es {retained['media']-absent['media']:.2f} años.")
    lines.append("La composición por edad difiere entre grupos en cada transición; por ello una "
                 "restricción de continuidad puede modificar el perfil analítico. La observación posterior "
                 "incluye entrevistas sobre fallecidos y los intervalos difieren: estos contrastes no "
                 "estiman supervivencia ni efectos de edad sobre abandono. La selección final exige "
                 "revisión de perfiles por sexo, educación, localidad y entrevista en las tablas.")
    return '\n\n'.join(lines)
