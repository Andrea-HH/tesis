"""Inventario mínimo de variables; validar cobertura por ola antes de usarlas."""
GRUPOS={
 'controles':['edad','sexo','est_conyugal','urbano','educacion'],
 'economia':['imp_neto','ocupacion','autoem','horas_trabajadas'],
 'salud_fisica':['n_enf','bmi_imp','salud_glob'],
 'salud_mental':['n_sint_depr','cesd_deprimido','solo'],
 'funcionalidad':['n_abvd','n_aivd','n_mov'],
 'cognicion':['recuerdo1','recuerdo2','orientacion','serial7'],
 'participacion':['cruci_rompe','juegos_mesa','asiste_cursos','asiste_club',
                  'comu_telef_comp','act_mant','cuida_adulto','cuida_menor',
                  'voluntario','cose','ve_tv','lee'],
}
