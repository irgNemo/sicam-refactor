"""Explicit export mapping: missing reference metrics are NOT approximated."""
SCHEMA_VERSION = 'saliva-nuclear-1'
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
        FEATURES.append(dict(key=entity+'_'+key,entity=entity,label=prefix+label,group=group,pixel=px,physical=um))
FEATURES += [dict(key='area_ratio',entity='relation',label='Relacion_area_MN_nucleo',group='Relaciones',pixel='area_fraction_to_nucleus',physical=None),
             dict(key='centroid_distance',entity='relation',label='Distancia_centroides_MN_nucleo',group='Relaciones',pixel='distance_to_nucleus_px',physical='distance_to_nucleus_um')]
UNAVAILABLE = ['Elipticidad','Solidez','Relacion_Proporcion_perimetro_MN_sobre_nucleo','Relacion_Distancia_borde_MN_nucleo_px']
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
