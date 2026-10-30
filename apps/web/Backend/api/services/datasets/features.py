"""Explicit export mapping: missing reference metrics are NOT approximated."""
SCHEMA_VERSION = 'saliva-nuclear-2'
GRAIN = 'NUCLEUS_MN_RELATION'
SPLIT_WARNING = 'Las particiones de entrenamiento/validación/prueba deben realizarse por paciente, no por fila, núcleo ni imagen.'
FEATURES = []
for entity, prefix in [('nucleus',''),('mn','MN_')]:
    for key, label, group, px, um in [
        ('area','Area','Morfología','area_px2','area_um2'),
        ('perimeter','Perimetro','Morfología','perimeter_px','perimeter_um'),
        ('eccentricity','Excentricidad','Morfología','eccentricity',None),
        ('circularity','Circularidad','Morfología','circularity',None),
        ('intensity','Intensidad_media_gris','Intensidad','mean_gray_intensity',None),
        ('std','Desv_std_intensidad','Intensidad','std_gray_intensity',None),
        *[(k,'GLCM_'+name,'Textura','texture.'+k,None) for k,name in
          [('contrast','Contraste'),('homogeneity','Homogeneidad'),('energy','Energia'),('correlation','Correlacion')]],
    ]:
        FEATURES.append(dict(key=entity+'_'+key,entity=entity,label=prefix+label,group=group,pixel=px,physical=um,min_version='2.1'))
FEATURES += [dict(key='area_ratio',entity='relation',label='Relacion_area_MN_nucleo',group='Relaciones',pixel='area_fraction_to_nucleus',physical=None,min_version='2.1'),
             dict(key='centroid_distance',entity='relation',label='Distancia_centroides_MN_nucleo',group='Relaciones',pixel='distance_to_nucleus_px',physical='distance_to_nucleus_um',min_version='2.1')]

# Sprint 18U-C1 — Characterization 2.3 new features
FEATURES += [
    dict(key='nucleus_elongation', entity='nucleus', label='Indice_elongacion',
         group='Morfología', pixel='elongation_index', physical=None, min_version='2.3'),
    dict(key='nucleus_solidity', entity='nucleus', label='Solidez_convexa',
         group='Morfología', pixel='convex_solidity', physical=None, min_version='2.3'),
    dict(key='mn_elongation', entity='mn', label='MN_Indice_elongacion',
         group='Morfología', pixel='elongation_index', physical=None, min_version='2.3'),
    dict(key='mn_solidity', entity='mn', label='MN_Solidez_convexa',
         group='Morfología', pixel='convex_solidity', physical=None, min_version='2.3'),
    dict(key='perimeter_ratio', entity='relation', label='Razon_perimetros_MN_nucleo',
         group='Relaciones', pixel='mn_nucleus_perimeter_ratio_px',
         physical='mn_nucleus_perimeter_ratio_physical', min_version='2.3'),
    dict(key='mn_separation', entity='relation', label='Separacion_minima_MN_nucleo',
         group='Relaciones', pixel='mn_nucleus_min_distance_px',
         physical='mn_nucleus_min_distance_um', min_version='2.3'),
]

# UNAVAILABLE is now empty — all four legacy gaps are closed by 2.3 features above.
UNAVAILABLE = []
CORE = ['ID_paciente','ID_foto','Nucleo','MN','Clase','Tiene_MN']


def columns(config, units):
    output = []
    for feature in FEATURES:  # fixed schema order, independent of checkbox order
        if feature['key'] not in config['features']: continue
        paths = [('pixel',feature['pixel'])]
        if feature['physical']:
            paths = [('pixel',feature['pixel'])] if units=='PIXELS' else [('physical',feature['physical'])]
            if units=='BOTH': paths=[('pixel',feature['pixel']),('physical',feature['physical'])]
        for mode,path in paths:
            suffix = ''
            if feature['physical']: suffix = '_'+path.rsplit('_',1)[-1]
            output.append({**feature,'column':feature['label']+suffix,'path':path,'physical_column':mode=='physical'})
    return output
