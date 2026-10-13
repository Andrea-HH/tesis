"""Ampliación incremental pensionaria v1; nunca ejecuta integración o titularidad."""
from __future__ import annotations
from tesis_enasem.project_paths import project_path, read_project_text, write_project_text, read_project_bytes

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from tesis_enasem.integration import person_id
from tesis_enasem.pension_exploration import (PopulationSpec, ownership_category, age_groups,
    categorical_table, continuous_table, conditional_associations, stratified_transitions, institutional_people)
from tesis_enasem.protection_eda import receipt_state, reception_rates, protection_crosstab, categorical_association
from tesis_enasem.joint_eda import paired_spearman
from run_protection_eda import COMPARABILITY, COMPARABILITY_REASONS

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = project_path('', 'docs/eda/pensiones_exploratorio_v1')
FIG = project_path('', 'reports/pensiones_exploratorio_v1/figuras')
YEARS = (2001,2003,2012,2015,2018,2021)
PROFILE = ['sexo_grupo','edad_quinquenal','educacion_grupo','localidad_grupo','ocupacion_grupo']
LABELS = {'sexo_grupo':'Sexo','edad_quinquenal':'Edad quinquenal','educacion_grupo':'Escolaridad inicial',
          'localidad_grupo':'Tamaño de localidad','ocupacion_grupo':'Condición de actividad',
          'est_conyugal_grupo':'Estado conyugal','salario_principal_estado':'Salario de trabajo principal'}
BIV = [('B1','Pensión × Sexo',['sexo_grupo']),('B2','Pensión × Edad',['edad_quinquenal']),
       ('B3','Pensión × Educación',['educacion_grupo']),('B4','Pensión × Tamaño de localidad',['localidad_grupo']),
       ('B5','Pensión × Apoyos gubernamentales',[]),('B6','Pensión × Institución otorgante',[]),
       ('B7','Pensión × Ocupación',['ocupacion_grupo']),('B8','Pensión × Patrimonio e ingresos',[])]
TRIV = [('T1','Pensión × Sexo × Educación',['sexo_grupo','educacion_grupo']),
        ('T2','Pensión × Edad × Sexo',['edad_quinquenal','sexo_grupo']),
        ('T3','Pensión × Educación × Localidad',['educacion_grupo','localidad_grupo']),
        ('T4','Pensión × Apoyo × Localidad',['localidad_grupo']),
        ('T5','Pensión × Apoyo × Sexo',['sexo_grupo']),
        ('T6','Pensión × Edad × Educación',['edad_quinquenal','educacion_grupo']),
        ('T7','Pensión × Ocupación × Edad',['ocupacion_grupo','edad_quinquenal']),
        ('T8','Pensión × Patrimonio × Educación',['educacion_grupo'])]


def serial(value: object) -> object:
    """Convierte escalares numpy sin insertar texto NaN en agregados públicos."""
    if isinstance(value, (np.integer,)): return int(value)
    if isinstance(value, (np.floating,)): return float(value) if np.isfinite(value) else None
    if isinstance(value, np.bool_): return bool(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, obj: object) -> None:
    """Exporta únicamente esquemas agregados; el llamador excluye claves personales."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # pandas puede producir NaN nativos: normalizar también esos escalares.
    text = json.dumps(obj, ensure_ascii=False, indent=2, default=serial)
    text = re.sub(r'(?<![\w"])NaN(?![\w"])', 'null', text)
    write_project_text(path, text)
    json.loads(text, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def checked_hashes() -> dict:
    """Compara todas las entradas históricas con la congelación previa a esta etapa."""
    hashes = json.loads(read_project_text(project_path('docs/eda/pensiones_exploratorio_v1', 'huellas_anteriores.json')))
    for p,h in hashes.items():
        if sha256(read_project_bytes(project_path('', p))).hexdigest() != h:
            raise ValueError(f'Entrada anterior modificada: {p}')
    return hashes


def inputs() -> tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]:
    """Añade controles por lookup 1:1 del maestro existente, sin unir las 17 fuentes."""
    private = project_path('', 'data/processed/armonizacion_economica_v1')
    p = pd.read_parquet(private/'personas_ronda.parquet')
    assert len(p)==99676 and p.id.nunique()==27171 and not p[['id','ronda']].duplicated().any()
    assert p.id.equals(person_id(p))
    dictionary = json.loads(read_project_text(project_path('', 'docs/integracion/diccionario_columnas.json')))
    metadata = {x['columna']:x for x in dictionary}
    controls = ['ocupacion','est_conyugal','imp_neto','salud_glob','diabetes','n_sint_depr','n_abvd','recuerdo1','edu_gru']
    fields = set(controls)
    for y, f in [(2001,'F12'),(2003,'F11'),(2012,'F07'),(2015,'F08'),(2018,'F09'),(2021,'F10')]:
        suf = f'_{y%100:02}' if y>=2012 else ''
        gates = ['k44','k50','k43','k49'] if y==2001 else ['k47','k53','k46','k52b']
        fields.update(f'{f}__{g}{suf}' for g in gates)
    tags = [metadata[f]['campo_tag'] for f in fields if metadata[f].get('campo_tag')]
    m = pd.read_parquet(project_path('', 'data/processed/enasem_integrada_provisional.parquet'),
                        columns=['id','ronda',*sorted(fields),*tags])
    for f in fields:
        tag = metadata[f].get('campo_tag')
        if tag:
            m[f] = pd.to_numeric(m[f], errors='coerce').where(m[tag].eq(0))
    p = p.merge(m[['id','ronda',*sorted(fields)]], on=['id','ronda'], how='left', validate='one_to_one')
    assert len(p)==99676
    p['edad_quinquenal'] = age_groups(p.edad)
    p['titularidad_grupo'] = [ownership_category(a,b) for a,b in zip(p.pension_propia_k,p.pension_conyuge_k)]
    p['S'] = p.pension_conyuge_k.map(receipt_state)
    codes = json.loads(read_project_text(project_path('', 'docs/eda/contratos_simple.json')))['contratos']
    for var in ('ocupacion','est_conyugal'):
        c = next(x for x in codes if x['variable']==var)
        p[var+'_grupo'] = p[var].map({float(k):v for k,v in c['codes'].items()}).fillna('Desconocido')
    p['salario_principal_estado'] = 'Desconocido'
    p['salario_elegible_confirmado'] = False
    for y,f in [(2001,'F12'),(2003,'F11'),(2012,'F07'),(2015,'F08'),(2018,'F09'),(2021,'F10')]:
        suf = f'_{y%100:02}' if y>=2012 else ''
        own,spouse,filter_own,filter_spouse = (['k44','k50','k43','k49'] if y==2001 else ['k47','k53','k46','k52b'])
        for role, gate, parent in [(1,own,filter_own),(2,spouse,filter_spouse)]:
            mask = p.ano.eq(y) & p.titularidad_rama.eq(role) & p.tipent.ne(5)
            eligible = mask & p[f'{f}__{parent}{suf}'].eq(1)
            p.loc[eligible,'salario_elegible_confirmado'] = True
            p.loc[eligible,'salario_principal_estado'] = p.loc[eligible,f'{f}__{gate}{suf}'].map({1:'Sí',2:'No'}).fillna('Desconocido')
    k = pd.read_parquet(private/'eventos_pensionarios.parquet')
    a = pd.read_parquet(private/'eventos_apoyos.parquet')
    return p,k,a


def concept_map() -> dict:
    """Organiza columnas trazables. Candidatos léxicos no equivalen a armonización."""
    d = json.loads(read_project_text(project_path('', 'docs/integracion/diccionario_columnas.json')))
    contracts = {c['variable']:c for c in json.loads(read_project_text(project_path('', 'docs/eda/contratos_simple.json')))['contratos']}
    versions = {(x['fuente'],x['variable']):x for x in json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/versiones_fuente.json')))}
    rules = [('Pensiones',r'pensi|pension|jubil|retirement|widow|disab.*benefit'),
        ('Apoyos gubernamentales',r'government|gubern|public donation|programa|prospera|proagro|inapam'),
        ('Patrimonio',r'wealth|patrimonio|net worth|assets|debt|business.*value|property|vivienda|vehicle.*value|real estate|bank account'),
        ('Ingresos',r'income|salary|earn|bonus|remittance|transfer|rent|ingreso|donation|dividend'),
        ('Educación',r'educ|school|literac'),('Ocupación y actividad laboral',r'employ|work|job|ocupaci|trabaj|labor'),
        ('Salud, funcionalidad y cognición',r'health|salud|diabet|hypert|arthri|depress|symptom|cogn|memory|recall|abvd|aivd|motor|smok|alcohol|bmi|cancer|stroke|enfer|hospital|funciona|sint|recuerdo|figure|serial|orientaci|tabaco'),
        ('Demografía',r'age|edad|sex|sexo|marital|conyugal|child|household|local|resident|birth|parent|sibling|nieto|hijo|fallec|entrevist')]
    rows=[]
    for x in d:
        name=x.get('variable_original',x['columna']); label=x.get('etiqueta','')
        product=x.get('producto','control_enlace'); technical=product in ('auxiliar_faltante','control_enlace','clave_derivada','calendario_nominal') or name in ('cunicah','np','ronda','acthog','codent01','codent03') or name.startswith(('subhog','factori','factorh'))
        text=(label+' '+name).lower()
        dim=next((dim for dim,pat in rules if re.search(pat,text)), 'Otros conceptos sustantivos pendientes de revisión')
        if technical: dim='Técnica / trazabilidad'
        c=contracts.get(name) if product=='maestra_ENASEMsimple' else None
        v=versions.get((x.get('fuente_id'),name))
        normalized=re.sub(r'_(?:01|03|12|15|18|21)$','',name)
        # Preservar ámbito/producto: no colapsar nombres que solamente se parecen.
        concept=(f'ENASEMsimple:{name}' if c else f'{product}:{normalized}')
        rows.append({'columna':x['columna'],'concepto_candidato':concept,'dimension':dim,
          'dimension_validada':bool(c or technical), 'variable_fuente':name,'archivo':x.get('archivo'),
          'fuente':x.get('fuente_id'),'ronda_ano':x.get('ano'), 'producto':product,
          'definicion':c['label'] if c else label or 'Pendiente de definición documental',
          'unidad':c['unit'] if c else x.get('unidad_fuente','Pendiente'),
          'titularidad':x.get('titularidad','Pendiente; no atribuir a persona por enlace'),
          'universo':c['eligibility'] if c else 'Pendiente por pregunta; disponibilidad no acredita elegibilidad',
          'categorias_originales':c['codes'] if c else x.get('etiquetas_valores',{}),
          'codigos_no_respuesta':c['numeric_nonresponse'] if c else 'Consultar libro por pregunta; no existe regla numérica universal',
          'tags_fuente':x.get('perfil_tags_fuente',{}),'cobertura':v,
          'ambito_cobertura':('Valores almacenados por personas-ronda 60+ enlazadas; no respuestas válidas ni universo elegible' if v else 'Tags en fuente original; no equivale a personas-ronda 60+ ni elegibles'),
          'comparabilidad':c['temporal'] if c else 'Pendiente; coincidencia de nombre no acredita equivalencia',
          'estado':'Contrato del indicador revisado; titularidad/universo indicado' if c else ('Técnica' if technical else 'Concepto candidato; semántica pendiente'),
          'enlace_eda_existente':f'docs/eda/variables/{name}.md' if c else None})
    assert len(rows)==8668 and len({r['columna'] for r in rows})==8668
    write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'mapa_columnas.json'),rows)
    summary=pd.DataFrame(rows).groupby(['dimension','producto']).size().reset_index(name='N_columnas').to_dict('records')
    write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'mapa_resumen.json'),summary)
    return {'N_columnas':len(rows),'N_candidatos':len({r['concepto_candidato'] for r in rows if r['dimension']!='Técnica / trazabilidad'}),
            'N_dimension_pendiente':sum(not r['dimension_validada'] for r in rows),'resumen':summary}


def plot_analysis(key: str, title: str, year: int, bundle: dict, groups: list[str]) -> None:
    """Una figura principal por solicitud; las tablas conservan todas las celdas."""
    fig,ax=plt.subplots(figsize=(10,5.5))
    colors=plt.get_cmap('BrBG')([.12,.42,.72,.92])
    if 'tasas' in bundle:
        r=pd.DataFrame(bundle['tasas']); fields=[g for g in groups if g in r]
        r['perfil']=r[fields].astype(str).agg(' / '.join,axis=1) if fields else 'Todos'
        variables=['pension_propia_k','pension_conyuge_k','apoyo_propio']
        r=r.loc[r.variable.isin(variables)]
        table=r.pivot(index='perfil',columns='variable',values='pct_si_conocido')
        # Trivariadas densas: mapa de calor, sin ocultar estratos ni sustituir por bivariable.
        if len(table)>10:
            fig.set_size_inches(10,max(6,.32*len(table)))
            image=ax.imshow(table.to_numpy(),aspect='auto',cmap='BrBG',vmin=0,vmax=100)
            ax.set_xticks(range(len(table.columns)),[{'pension_propia_k':'Propia K','pension_conyuge_k':'Cónyuge K','apoyo_propio':'Apoyo A'}[v] for v in table.columns])
            ax.set_yticks(range(len(table)),table.index,fontsize=8)
            for i in range(len(table)):
                for j in range(len(table.columns)):
                    if pd.notna(table.iloc[i,j]): ax.text(j,i,f'{table.iloc[i,j]:.1f}',ha='center',va='center',fontsize=7)
            fig.colorbar(image,ax=ax,label='% dentro del perfil, respuestas conocidas')
        else:
            table.rename(columns={'pension_propia_k':'Propia K','pension_conyuge_k':'Cónyuge K','apoyo_propio':'Apoyo A'}).plot.bar(ax=ax,color=colors,width=.8)
            ax.set_ylabel('% de recepción entre respuestas conocidas'); ax.tick_params(axis='x',rotation=25)
            ax.legend(fontsize=8)
    elif 'patrimonio' in bundle:
        r=pd.DataFrame(bundle['patrimonio']); fields=['titularidad_grupo',*groups]
        r['perfil']=r[fields].astype(str).agg(' / '.join,axis=1)
        r=r.loc[r.N_valido.gt(0)]
        ax.barh(r.perfil,r.mediana,color=colors[0]); ax.set_xlabel('Mediana patrimonial; unidades almacenadas, sin deflactar')
        fig.set_size_inches(11,max(5,.3*len(r))); ax.tick_params(axis='y',labelsize=8)
    elif 'instituciones' in bundle:
        r=pd.DataFrame(bundle['instituciones'])
        if len(r):
            r['nombre']=r.institucion_codigo.map({1:'IMSS',2:'ISSSTE'}).fillna(r.institucion_codigo.map(lambda c:f'Código {c}'))
            r.plot.bar(x='nombre',y='N_personas',ax=ax,color=colors[0],legend=False)
            ax.set_ylabel('Personas receptoras; selección múltiple no aditiva')
        else: ax.text(.5,.5,'Sin institución identificada',ha='center')
    elif 'conjunta' in bundle:
        r=pd.DataFrame(bundle['conjunta']); groups_actual=[g for g in groups if g in r]
        r['perfil']=r[groups_actual].astype(str).agg(' / '.join,axis=1) if groups_actual else 'Todos'
        r['estado']=r.pension+' / '+r.apoyo
        table=r.pivot(index='perfil',columns='estado',values='pct_estrato')
        table.plot.bar(ax=ax,stacked=True,colormap='BrBG',fontsize=8)
        ax.set_ylabel('% de todos los registros del perfil');ax.legend(fontsize=6,ncol=3)
    elif 'frecuencias' in bundle:
        r=pd.DataFrame(bundle['frecuencias']);r.plot.bar(x='categoria',y='N',ax=ax,color=colors[0],legend=False)
        ax.set_ylabel('Personas de 60+; incluye desconocidos')
    ax.set_title(f'{title} · {year}',fontsize=13); ax.set_xlabel('')
    n_total=0
    if bundle.get('tasas'):
        n_total=sum(z['N_total'] for z in bundle['tasas'] if z['variable']=='pension_propia_k')
    elif bundle.get('patrimonio'):n_total=sum(z['N_total'] for z in bundle['patrimonio'])
    elif bundle.get('instituciones'):n_total=bundle['instituciones'][0]['N_total_estrato']
    elif bundle.get('conjunta'):n_total=sum(z['N'] for z in bundle['conjunta'])
    elif bundle.get('frecuencias'):n_total=sum(z['N'] for z in bundle['frecuencias'])
    ax.set_title(f'{title} · {year} · N total 60+={n_total:,}',fontsize=12)
    fig.text(.01,.01,'Muestra sin pesos. Denominador indicado en eje; N conocidos/ND en tabla. Instituciones: personas, selección múltiple no aditiva.',fontsize=8)
    fig.tight_layout(rect=[0,.05,1,1]); fig.savefig(project_path('reports/pensiones_exploratorio_v1/figuras', f'{key}.png'),dpi=150);plt.close(fig)


def narrative(title: str, year: int, part: pd.DataFrame, bundle: dict, groups: list[str]) -> str:
    """Interpretación numérica específica, con límites y pregunta derivada."""
    prose=[f'En {year}, {title.lower()} se explora entre {len(part):,} personas de 60 años o más observadas en esa ronda '
           f'({part.id.nunique():,} personas únicas; una fila por persona). No es una estimación poblacional ponderada.']
    if bundle.get('tasas'):
        rows=[r for r in bundle['tasas'] if r['variable']=='pension_propia_k' and r['N_conocido']>0 and all(r.get(g)!='Desconocido' for g in groups)]
        if rows:
            high=max(rows,key=lambda r:r['pct_si_conocido']);low=min(rows,key=lambda r:r['pct_si_conocido'])
            name=lambda r:' / '.join(str(r.get(g,'')) for g in groups) or 'todos'
            prose.append(f'La recepción propia K entre respuestas conocidas alcanza {high["N_si"]:,}/{high["N_conocido"]:,} '
                f'({high["pct_si_conocido"]:.2f}%) en {name(high)}, frente a {low["N_si"]:,}/{low["N_conocido"]:,} '
                f'({low["pct_si_conocido"]:.2f}%) en {name(low)}: diferencia descriptiva de '
                f'{high["pct_si_conocido"]-low["pct_si_conocido"]:.2f} puntos porcentuales. '
                f'Los desconocidos respectivos son {high["N_desconocido"]:,} y {low["N_desconocido"]:,}. '
                'La tabla distingue esa tasa de la composición de receptores y presenta la rama del cónyuge por separado.')
            if len(groups)>1:
                # Condicionamiento real en la segunda dimensión, evitando una prosa meramente marginal.
                g1,g2=groups[:2]; candidates=[]
                for level in sorted({str(r[g2]) for r in rows}):
                    sub=[r for r in rows if str(r[g2])==level]
                    if len(sub)>1:
                        hi=max(sub,key=lambda r:r['pct_si_conocido']);lo=min(sub,key=lambda r:r['pct_si_conocido'])
                        candidates.append((hi['pct_si_conocido']-lo['pct_si_conocido'],level,hi,lo))
                if candidates:
                    large=max(candidates,key=lambda x:x[0]);small=min(candidates,key=lambda x:x[0])
                    prose.append(f'Al fijar {LABELS.get(g2,g2).lower()} en {large[1]}, la amplitud entre categorías de '
                        f'{LABELS.get(g1,g1).lower()} es {large[0]:.2f} pp, mientras en {small[1]} es {small[0]:.2f} pp. '
                        'Este contraste condicionado describe heterogeneidad, no prueba interacción causal o significancia; '
                        'las celdas pequeñas y sus N conocidos están visibles en el respaldo.')
    if bundle.get('conjunta'):
        total=sum(r['N'] for r in bundle['conjunta']); both=sum(r['N'] for r in bundle['conjunta'] if r['pension']=='Sí' and r['apoyo']=='Sí')
        supp=sum(r['N'] for r in bundle['conjunta'] if r['pension']=='No' and r['apoyo']=='Sí')
        nd=sum(r['N'] for r in bundle['conjunta'] if 'Desconocido' in (r['pension'],r['apoyo']))
        prose.append(f'Las nueve combinaciones K/A reconcilian {total:,} registros: {both:,} presentan ambas afirmativas, '
            f'{supp:,} apoyo y negativa explícita K, y {nd:,} desconocimiento de al menos una respuesta. '
            'Una negativa K no acredita ausencia de cualquier pensión; el apoyo puede incluir dinero o especie.')
        if groups:
            details=[]
            for level in sorted({str(r[groups[0]]) for r in bundle['conjunta']}):
                sub=[r for r in bundle['conjunta'] if str(r[groups[0]])==level and r['apoyo']!='Desconocido' and r['pension']!='Desconocido']
                rates=[]
                for state in ['Sí','No']:
                    den=sum(r['N'] for r in sub if r['pension']==state);num=sum(r['N'] for r in sub if r['pension']==state and r['apoyo']=='Sí')
                    rates.append((num,den,100*num/den if den else None))
                if all(x[2] is not None for x in rates):
                    details.append(f'{level}: A entre K sí {rates[0][0]:,}/{rates[0][1]:,} ({rates[0][2]:.2f}%), '
                                   f'entre K no {rates[1][0]:,}/{rates[1][1]:,} ({rates[1][2]:.2f}%)')
            prose.append('Condicionando simultáneamente por '+LABELS[groups[0]].lower()+': '+'; '.join(details)+'.')
    if bundle.get('patrimonio'):
        for r in bundle['patrimonio']:
            if r['N_valido'] and not groups and r['titularidad_grupo']!='Desconocido':
                prose.append(f'{r["titularidad_grupo"]}: mediana patrimonial {r["mediana"]:,.2f}, '
                    f'IQR [{r["p25"]:,.2f}, {r["p75"]:,.2f}], N válido {r["N_valido"]:,}/{r["N_total"]:,}.')
        prose.append('El patrimonio pertenece al entrevistado y su cónyuge, si lo hay; los registros no son hogares distintos. '
            'Se conservan ceros y negativos. Los contrastes son internos a la ronda; no se calcula crecimiento real ni vulnerabilidad.')
        if groups:
            edu=groups[0]; details=[]
            for level in sorted({str(r[edu]) for r in bundle['patrimonio']}):
                vals=[r for r in bundle['patrimonio'] if str(r[edu])==level and r['N_valido'] and r['titularidad_grupo']!='Desconocido']
                if len(vals)>1:
                    hi=max(vals,key=lambda r:r['mediana']);lo=min(vals,key=lambda r:r['mediana'])
                    details.append(f'{level}: {hi["titularidad_grupo"]} {hi["mediana"]:,.2f} (N={hi["N_valido"]:,}) '
                                   f'frente a {lo["titularidad_grupo"]} {lo["mediana"]:,.2f} (N={lo["N_valido"]:,})')
            prose.append('La distribución se condiciona por escolaridad y rama pensionaria a la vez. Extremos de medianas dentro de escolaridad: '+'; '.join(details)+'.')
    if bundle.get('instituciones'):
        vals=bundle['instituciones']; top=max(vals,key=lambda r:r['N_personas'])
        prose.append(f'La categoría institucional más numerosa del cuadro es código {top["institucion_codigo"]}, '
          f'{top["N_personas"]:,}/{top["N_receptoras_institucion_identificada"]:,} receptoras con institución identificada '
          f'({top["pct_receptoras_con_institucion"]:.2f}%). Las afiliaciones múltiples no forman una partición; '
          'no se multiplica un monto por cada institución. IMSS/ISSSTE permite identificar sistema, no régimen individual.')
    if bundle.get('asociaciones'):
        values=[r for r in bundle['asociaciones'] if r.get('V_cramer') is not None]
        if values:
            lo=min(values,key=lambda r:r['V_cramer']);hi=max(values,key=lambda r:r['V_cramer'])
            prose.append(f'V de Cramér entre pensión propia y la característica estudiada oscila de '
                         f'{lo["V_cramer"]:.4f} (N={lo["N_validos"]:,}) a {hi["V_cramer"]:.4f} '
                         f'(N={hi["N_validos"]:,}) dentro de los estratos evaluables. '
                         'No se ejecutan pruebas de significancia ni selección confirmatoria entre múltiples contrastes.')
    for r in bundle.get('spearman',[]):
        if r.get('rho_spearman') is not None:
            prose.append(f'Spearman {r.get("variable_x")}–{r.get("variable_y")}: ρ={r["rho_spearman"]:.4f}, N válido={r.get("N_pares_validos",0):,}; asociación de rangos dentro de ronda.')
    prose.append('Los posibles mecanismos laborales, familiares o de selección quedan como hipótesis. '
        '2001/J1, punteros discordantes, 33 firmas candidatas de 2015, tipos ambiguos, ponderación y precios siguen pendientes. '
        'La escolaridad es inicial y localidad usa 100 mil habitantes; ocupación no identifica profesión ni retiro pensionado. '
        f'Pregunta derivada: ¿se conserva el patrón de {title.lower()} al seguir a las mismas personas y separar cambios de instrumento, '
        'titularidad y selección? No se adopta aún como pregunta definitiva.')
    return '\n\n'.join(prose)


def run() -> None:
    """Genera nuevos agregados por etapas conservando los anteriores byte a byte."""
    PUBLIC.mkdir(parents=True,exist_ok=True);FIG.mkdir(parents=True,exist_ok=True)
    hashes=checked_hashes(); mapping=concept_map();p,k,a=inputs();s=PopulationSpec().select(p)
    assert len(s)==56004 and s.id.nunique()==18754
    old=json.loads(read_project_text(project_path('', 'docs/eda/proteccion_economica/resultados.json')))
    result={'poblacion':{'N_maestro':len(p),'N_personas_maestro':p.id.nunique(),'N_personas_ronda_60':len(s),
        'N_personas_60':s.id.nunique(),'ponderado':False,'edad_minima':60},'mapa':mapping,'analisis':{},'seguimiento':{},'univariados':{},'validacion':{}}
    for year in YEARS:
        part=s.loc[s.ano.eq(year)].copy(); e=k.loc[k.ano.eq(year)&k.beneficiario_id.isin(part.id)].copy()
        supports=a.loc[a.ano.eq(year)&a.beneficiario_id.isin(part.id)].copy()
        ep=e.merge(part[['id','ano','tipent',*PROFILE,'est_conyugal_grupo']],left_on=['beneficiario_id','ano'],right_on=['id','ano'],validate='many_to_one')
        ep['tipo_grupo']=ep.tipo.map({1:'Jubilación/retiro',2:'Viudez/supervivencia',3:'Invalidez',4:'Otra pensión'})
        ep['monto']=ep.monto_mensual_observado
        # Los eventos ya fueron deduplicados por slot en la auditoría; no borrar firmas iguales.
        counts=e.groupby('beneficiario_id').size()
        part['eventos_observados']=part.id.map(counts)
        part['numero_eventos_estado']=part.eventos_observados.map(lambda x:str(int(x)) if pd.notna(x) else 'Desconocido')
        part.loc[part.pension_propia_k.eq(False),'numero_eventos_estado']='0 (negativa K)'
        univ={'titularidad':categorical_table(part,'titularidad_grupo'),
              'eventos_observados_no_numero_declarado':categorical_table(part,'numero_eventos_estado'),
              'estados_titular':categorical_table(part,'titularidad_estado'),
              'instituciones':institutional_people(e,part),
              'montos_por_contingencia':continuous_table(ep,'monto',['tipo_grupo']),
              'controles':{},'recibos_reutilizados':[r for r in old['recepcion'] if r['ano']==year],
              'programas_reutilizados':[r for r in old['programas'] if r['ano']==year]}
        for var in ['edad','educacion','ocupacion_grupo','sexo_grupo','localidad_grupo','imp_neto','salud_glob','diabetes','n_sint_depr','n_abvd','recuerdo1']:
            univ['controles'][var]=categorical_table(part,var) if var.endswith('_grupo') or var in ['salud_glob','diabetes'] else continuous_table(part,var)
        result['univariados'][str(year)]=univ
        plot_analysis(f'U_titularidad_{year}','Recepción propia y del cónyuge',year,{'frecuencias':univ['titularidad']},[])
        plot_analysis(f'U_eventos_{year}','Número de eventos/slots observados; no número declarado',year,{'frecuencias':univ['eventos_observados_no_numero_declarado']},[])
        # Histograma BrBG del evento mensual nominal, sin recortar extremos en el cálculo.
        for block,events in [('K',e),('A',supports)]:
            values=events.monto_mensual_observado.dropna()
            fig,ax=plt.subplots(figsize=(8,4));v=np.log1p(values)
            ax.hist(v,bins=25,color=plt.get_cmap('BrBG')(.12));ax.set_xlabel('log(1 + monto mensual nominal); conserva ceros')
            ax.set_ylabel('Eventos de beneficiarios 60+');ax.set_title(f'{block}: montos por evento · {year} · N válido={len(values):,}/{len(events):,}')
            fig.tight_layout();fig.savefig(project_path('reports/pensiones_exploratorio_v1/figuras', f'U_montos_{block}_{year}.png'),dpi=150);plt.close(fig)
            univ[f'histograma_{block}']=[{'log1p_limite_inferior':float(lo),'log1p_limite_superior':float(hi),'N_eventos':int(n)} for n,lo,hi in zip(*[np.histogram(v,bins=25)[0],np.histogram(v,bins=25)[1][:-1],np.histogram(v,bins=25)[1][1:]])]
        for code,title,groups in BIV+TRIV:
            bundle={}; key=f'{code}_{year}'
            if code in ['B5','T4','T5']:
                oldkey=f'{year}_pension_apoyo'+('' if not groups else '_'+groups[0])
                bundle['conjunta']=old['cruces'][oldkey]
                bundle['reutiliza']=f'docs/eda/proteccion_economica/tablas/{oldkey}.json'
                bundle['asociaciones']=conditional_associations(part,'A',groups)
            elif code=='B6':
                bundle['instituciones']=univ['instituciones']
                bundle['tipos']=continuous_table(ep,'monto',['tipo_grupo'])
                bundle['limite']='Institución solo definida en receptoras: no es una asociación binaria independiente con recepción. Instituciones múltiples sin suma de montos.'
            elif code in ['B8','T8']:
                bundle['patrimonio']=continuous_table(part,'imp_neto',['titularidad_grupo',*groups])
                bundle['monto_por_titularidad']=continuous_table(part,'monto_k_propio_mensual_observado_parcial',['titularidad_grupo',*groups])
                bundle['spearman']=[paired_spearman(part,'imp_neto','monto_k_propio_mensual_observado_parcial',year)]
                if code=='B8':
                    salary=part.loc[part.salario_elegible_confirmado].copy()
                    bundle['salario_recepcion']=reception_rates(salary,['salario_principal_estado']) if len(salary) else []
                    bundle['N_elegible_salario_confirmado']=len(salary);bundle['N_sin_elegibilidad_salario_confirmada']=len(part)-len(salary)
                    bundle['limite_ingreso']='Solo recepción de salario de trabajo principal en rama propia y con filtro asalariado afirmativo. Montos salariales mes/año sin periodicidad homologada: no se comparan ni suman; no es ingreso total.'
            else:
                oldkey=f'{year}_recepcion_{groups[0]}' if len(groups)==1 else None
                bundle['tasas']=old['cruces'][oldkey] if oldkey in old['cruces'] else reception_rates(part,groups)
                if oldkey in old['cruces']:bundle['reutiliza']=f'docs/eda/proteccion_economica/tablas/{oldkey}.json'
                bundle['titularidad']=categorical_table(part,'titularidad_grupo',groups)
                bundle['asociaciones']=conditional_associations(part,groups[0],groups[1:])
                bundle['instituciones_por_perfil']=institutional_people(e,part,groups)
                bundle['montos_evento']=continuous_table(ep,'monto',groups)
                bundle['tipos_por_perfil']=categorical_table(ep,'tipo_grupo',groups)
                bundle['eventos_por_persona']=categorical_table(part,'numero_eventos_estado',groups)
                if code=='B2':bundle['spearman']=[paired_spearman(part,'edad','monto_k_propio_mensual_observado_parcial',year)]
            bundle['ano']=year;bundle['solicitud']=title;bundle['grupos']=groups
            bundle['interpretacion']=narrative(title,year,part,bundle,groups)
            plot_analysis(key,title,year,bundle,groups)
            write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'tablas', f'{key}.json'),bundle)
            result['analisis'][key]={'solicitud':title,'N_total':len(part),'tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json',
                'figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png','interpretacion':bundle['interpretacion'],
                'estado':'Parcial' if code=='B8' else 'Completo provisional'}
        # Complementarios verdaderamente simultáneos; tabla institucional no asigna montos por proveedor.
        for code,title,groups,kind in [
            ('C1','Institución × Sexo × Educación',['sexo_grupo','educacion_grupo'],'institucion'),
            ('C2','Institución × Edad × Localidad',['edad_quinquenal','localidad_grupo'],'institucion'),
            ('C3','Monto pensionario × Sexo × Educación',['sexo_grupo','educacion_grupo'],'monto'),
            ('C4','Titularidad × Sexo × Estado conyugal',['sexo_grupo','est_conyugal_grupo'],'titularidad')]:
            key=f'{code}_{year}'
            bundle={'instituciones':institutional_people(e,part,groups)} if kind=='institucion' else (
                {'montos':continuous_table(ep,'monto',groups)} if kind=='monto' else {'frecuencias':categorical_table(part,'titularidad_grupo',groups)})
            # Las tablas multidimensionales se visualizan como mapa/facetas; no se suman estratos.
            rows=pd.DataFrame(next(iter(bundle.values())))
            fig,ax=plt.subplots(figsize=(11,max(5,.22*len(rows))))
            if len(rows):
                rows['perfil']=rows[groups].astype(str).agg(' / '.join,axis=1)
                if kind=='institucion':table=rows.pivot(index='perfil',columns='institucion_codigo',values='pct_receptoras_con_institucion')
                elif kind=='monto':table=rows.set_index('perfil')[['mediana']]
                else:table=rows.pivot(index='perfil',columns='categoria',values='pct_total')
                image=ax.imshow(table.to_numpy(),aspect='auto',cmap='BrBG')
                ax.set_yticks(range(len(table)),table.index,fontsize=7);ax.set_xticks(range(len(table.columns)),table.columns,rotation=30,fontsize=8)
                fig.colorbar(image,ax=ax,label='Mediana mensual nominal por evento' if kind=='monto' else '% condicional; denominadores en respaldo')
            ax.set_title(f'{title} · {year}');fig.tight_layout();fig.savefig(project_path('reports/pensiones_exploratorio_v1/figuras', f'{key}.png'),dpi=150);plt.close(fig)
            bundle.update(ano=year,grupos=groups,solicitud=title)
            valid=rows.loc[rows.get('N_valido',pd.Series(1,index=rows.index)).gt(0)]
            if kind=='monto' and len(valid):
                hi=valid.loc[valid.mediana.idxmax()];lo=valid.loc[valid.mediana.idxmin()]
                prose=f'Mediana mensual por evento: {hi.mediana:,.2f} en {hi.perfil}, N={hi.N_valido:,}, frente a {lo.mediana:,.2f} en {lo.perfil}, N={lo.N_valido:,}. Un beneficiario puede aportar varios eventos; no es mediana de ingreso total personal ni comparación real entre ondas.'
            elif kind=='institucion' and len(rows):
                top=rows.loc[rows.N_personas.idxmax()]
                prose=f'La celda más numerosa es código institucional {top.institucion_codigo} en {top.perfil}: {top.N_personas:,}/{top.N_receptoras_institucion_identificada:,} personas receptoras con institución identificada ({top.pct_receptoras_con_institucion:.2f}%). No es tasa en toda la población; selección múltiple por contingencia en 2012/2015 impide vincular cada institución a un monto.'
            elif len(rows):
                both=rows.loc[rows.categoria.eq('Ambas')]
                top=both.loc[both.N.idxmax()] if len(both) else rows.iloc[0]
                prose=f'{top.categoria} en {top.perfil}: {top.N:,}/{top.N_total:,} ({top.pct_total:.2f}%). Los estados desconocidos no se reclasifican como ausencia ni se atribuyen pensiones por estado conyugal.'
            else:prose='Sin celdas evaluables; no se obtiene asociación.'
            bundle['interpretacion']=f'{title}, {year}: '+prose+' Descriptivo sin ponderar; las tres dimensiones se usan simultáneamente. Titularidad definitiva pendiente.'
            write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'tablas', f'{key}.json'),bundle)
            result['analisis'][key]={'solicitud':title,'N_total':len(part),'tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json',
                'figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png','interpretacion':bundle['interpretacion'],'estado':'Completo provisional'}
        write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'tablas', f'U_{year}.json'),univ)
        print(f'Ronda {year}: N 60+={len(part):,}; 8 bivariados, 8 trivariados y 4 complementarios con respaldo.',flush=True)
    # Perfiles longitudinales en origen, siempre persona real; no exige seis visitas.
    correspond=[]
    for ya,yb in zip(YEARS[:-1],YEARS[1:]):
        start=s.loc[s.ano.eq(ya)&s.tipent.ne(5)];end=p.loc[p.ano.eq(yb)].set_index('id')
        present=start.id.isin(end.index);dead=start.id.isin(end.loc[end.tipent.eq(5)].index)
        correspond.append({'ano_origen':ya,'ano_destino':yb,'intervalo_anos':yb-ya,'N_origen_60_vivo':len(start),
            'N_presente_destino':int(present.sum()),'N_sobre_fallecido_destino':int(dead.sum()),'N_ausente_destino':int((~present).sum()),
            'N_reaparece_posterior':int((~present & start.id.isin(p.loc[p.ano.gt(yb),'id'])).sum())})
        for variable,contract_var in [('P','pension_propia_k'),('S','pension_propia_k'),('A','apoyo_propio'),('titularidad_grupo','pension_propia_k')]:
            comparable=COMPARABILITY[contract_var][(ya,yb)]
            for group in PROFILE[:4]:
                key=f'L_{variable}_{group}_{ya}_{yb}'
                rows=stratified_transitions(p,ya,yb,variable,group,comparable)
                write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'tablas', f'{key}.json'),rows)
                # Simultáneamente origen×destino×perfil. Facetas por perfil de origen.
                levels=sorted({r[group] for r in rows});fig,axes=plt.subplots(len(levels),1,figsize=(12,max(5,2.9*len(levels))),squeeze=False)
                for ax,lev in zip(axes[:,0],levels):
                    table=pd.DataFrame([r for r in rows if r[group]==lev]).pivot(index='origen',columns='destino',values='N').fillna(0)
                    ax.imshow(table,aspect='auto',cmap='BrBG');ax.set_yticks(range(len(table)),table.index,fontsize=7)
                    ax.set_xticks(range(len(table.columns)),table.columns,rotation=20,ha='right',fontsize=7)
                    for i in range(len(table)):
                        for j in range(len(table.columns)): ax.text(j,i,str(int(table.iloc[i,j])),ha='center',va='center',fontsize=7)
                    ax.set_title(f'{lev} · N origen={sum(r["N"] for r in rows if r[group]==lev):,}',fontsize=9)
                fig.suptitle(f'{variable} · {ya}–{yb} · {LABELS[group]} en origen · '+('comparabilidad condicionada' if comparable else 'ruptura de instrumento'))
                fig.tight_layout(rect=[0,0,1,.97]);fig.savefig(project_path('reports/pensiones_exploratorio_v1/figuras', f'{key}.png'),dpi=140);plt.close(fig)
                starts=sum(r['N'] for r in rows if r['evento']=='Inicio observado');continu=sum(r['N'] for r in rows if r['evento']=='Continuidad observada');loss=sum(r['N'] for r in rows if r['evento']=='Pérdida observada')
                summary=f'Cohorte 60+ viva en {ya}: {len(start):,}. '
                summary+=(f'Inicio observado {starts:,}, continuidad {continu:,}, pérdida observada {loss:,}. ' if comparable and variable!='titularidad_grupo' else 'No se interpreta inicio/pérdida a través de una ruptura de instrumento. ' if not comparable else 'Cambios entre ramas propia/cónyuge mantienen negativas y desconocidos separados. ')
                summary+=COMPARABILITY_REASONS[(contract_var,ya)]+'. Los perfiles se fijan en origen. Muerte registrada y ausencia no son pérdida de recepción. El denominador de cada fila de transición está en N_origen_estado; no se requieren seis rondas completas.'
                result['seguimiento'][key]={'solicitud':f'{variable} {ya}–{yb} por {LABELS[group]}','tabla':f'docs/eda/pensiones_exploratorio_v1/tablas/{key}.json',
                    'figura':f'reports/pensiones_exploratorio_v1/figuras/{key}.png','interpretacion':summary,
                    'estado':'Completo provisional' if comparable else 'No viable con los datos actuales'}
    result['correspondencias']=correspond
    # Tabla + visual comparativa de ramas: composición por ronda, nunca transición.
    fig,ax=plt.subplots(figsize=(10,5))
    tables=[]
    for year in YEARS:
        for r in result['univariados'][str(year)]['titularidad']:tables.append({'ano':year,**r})
    pd.DataFrame(tables).pivot(index='ano',columns='categoria',values='pct_total').plot.bar(stacked=True,ax=ax,colormap='BrBG')
    ax.set_ylabel('% de todos los registros 60+ de cada ronda');ax.set_title('Ramas pensionarias propias/cónyuge: composición transversal')
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(project_path('reports/pensiones_exploratorio_v1/figuras', 'U_comparacion_ramas.png'),dpi=150);plt.close(fig)
    write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'tablas/U_comparacion_ramas.json'),tables)
    result['validacion']={'maestro_preservado':True,'clave_unica':True,'id_formato_verificado':True,
        'seleccion_60_reconciliada':True,'rondas_N':[{'ano':y,'N':int(s.ano.eq(y).sum())} for y in YEARS],
        'entradas_historicas_sin_cambios':len(checked_hashes()),'clasificacion_definitiva':False}
    write_json(project_path('docs/eda/pensiones_exploratorio_v1', 'resultados.json'),result)
    print('Agregados nuevos guardados; entradas previas intactas.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        checked_hashes();print('Huellas históricas conservadas.')
    else:run()
