"""Reproduce baseline then run 18S-A.1 experiments; no Django or data writes."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .engine import measure_image, consensus, percent_difference
from .common import scales
from .diagnostics import save_diagnostic
from .review import review_grid, circle_sensitivity, diameter_perturbation


def font(size):
    return ImageFont.truetype('DejaVuSans.ttf',size)


def grid_diagrams(source, review, output):
    """Schematic separates observed marks from missing inferred subdivisions."""
    width, height = 1600, 1040
    image=Image.new('RGB',(width,height),'white'); draw=ImageDraw.Draw(image)
    draw.text((35,15),'GRID: observed marks and missing subdivisions (original pixel coordinates)',fill='black',font=font(23))
    draw.text((35,52),'Red: long/major | Blue: short/minor | Gray: inferred, NOT observed | Magenta: rejected',fill='black',font=font(18))
    local=Image.new('RGB',(1600,960),'white'); ld=ImageDraw.Draw(local)
    ld.text((35,15),'Local unit pitch: observed adjacent intervals vs gap/index-span estimates',fill='black',font=font(22))
    with Image.open(source) as original:
        overlay=original.convert('RGB')
    od=ImageDraw.Draw(overlay)
    matrix=np.asarray(review['original_to_aligned']); inverse=np.linalg.inv(np.vstack((matrix,[0,0,1])))
    center=matrix @ np.array([overlay.width/2,overlay.height/2,1])
    for axis,row in zip(('x','y'),(140,600)):
        data=review['axes'][axis]; marks=data.get('marks',[])
        if not marks:
            draw.text((35,row),f'{axis.upper()}: insufficient hierarchy evidence',fill='black',font=font(20));continue
        lo,hi=marks[0]['position_px'],marks[-1]['position_px']
        xcoord=lambda p:70+(p-lo)/(hi-lo)*1460
        draw.text((35,row-45),f"{axis.upper()} | {data['geometry_status']} | complete observed groups: {data['complete_observed_groups']}",fill='black',font=font(19))
        draw.line((70,row+110,1530,row+110),fill='black',width=2)
        for mark in marks:
            x=xcoord(mark['position_px']); major=mark['kind']=='major'
            color='magenta' if not mark['accepted'] else ('red' if major else 'blue')
            draw.line((x,row+110,x,row+(20 if major else 65)),fill=color,width=3)
            draw.text((x-15,row+120),str(mark['index']),fill=color,font=font(16))
            draw.text((x-26,row+155+(mark['index']%2)*22),f"{mark['position_px']:.1f}",fill=color,font=font(13))
            aligned=np.r_[([mark['position_px'],center[1]] if axis=='x' else [center[0],mark['position_px']]),1]
            px,py,_=inverse @ aligned
            od.ellipse((px-12,py-12,px+12,py+12),fill=color)
            od.text((px+18,py+18),f"{axis.upper()}{mark['index']}",fill=color,font=font(38))
        for i,g in enumerate(data['groups']):
            xa,xb=xcoord(g['left_px']),xcoord(g['right_px']);y=row+240+(i%2)*45
            color='green' if g['fully_observed_five_intervals'] else 'gray'
            draw.line((xa,y,xb,y),fill=color,width=3)
            draw.text(((xa+xb)/2-55,y+4),'5 observed' if color=='green' else '5 inferred',fill=color,font=font(14))
            for index in g['missing_interior_indices']:
                pos=g['left_px']+(index-g['left_index'])*(g['right_px']-g['left_px'])/5
                x=xcoord(pos)
                draw.line((x,row+95,x,row+110),fill='gray',width=1)
                draw.text((x-9,row+80),str(index),fill='gray',font=font(11))
        intervals=data['spatial_variation']['intervals']; values=[i['pitch_per_minor_index_px'] for i in intervals]
        top=90 if axis=='x' else 520
        vmin,vmax=min(values)-1,max(values)+1
        yc=lambda v:top+260-(v-vmin)/(vmax-vmin)*240
        ld.text((35,top-30),f'{axis.upper()} — unit pitch px (not optical distortion attribution)',fill='black',font=font(19))
        ld.line((70,top,70,top+260,1530,top+260),fill='black',width=2)
        for tick in np.linspace(vmin,vmax,5):
            y=yc(tick);ld.text((5,y-8),f'{tick:.1f}',fill='black',font=font(14));ld.line((70,y,1530,y),fill='#dddddd')
        for item in intervals:
            x=xcoord(item['midpoint_px']);y=yc(item['pitch_per_minor_index_px'])
            color='blue' if item['observed_single_interval'] else 'orange'
            ld.ellipse((x-6,y-6,x+6,y+6),fill=color)
            ld.text((x-18,y+10),f"/{item['index_span']}",fill=color,font=font(14))
        for tick in np.linspace(lo,hi,6):
            ld.text((xcoord(tick)-25,top+275),f'{tick:.0f}',fill='black',font=font(14))
        ld.text((70,top+310),'Position px | blue: observed span 1 | orange: span >1, missing marks inferred',fill='black',font=font(16))
    image.save(output/'grid-hierarchy.png');local.save(output/'grid-local-pitch.png')
    overlay.thumbnail((1600,1600));overlay.save(output/'grid-indexed-overlay.png')


def table(headers, rows):
    def cell(v):
        return f'{v:.12g}' if isinstance(v,float) else str(v)
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
                     ['| '+' | '.join(cell(v) for v in row)+' |' for row in rows])


def scientific_findings(grid, circles, sensitivity):
    """Descriptive comparisons, never corrections or scientific thresholds."""
    by_diameter = {r['known_dimension_um']: r for r in circles}
    findings = {'grid_axis_only_comparisons': [], 'metrological_uncertainty': 'NOT_ESTIMATED'}
    for axis, data in grid['axes'].items():
        value = data.get('scale_minor_um_per_px')
        if value is not None:
            for circle in circles:
                findings['grid_axis_only_comparisons'].append(dict(axis=axis, circle=circle['source_file'],
                    symmetric_difference_percent=percent_difference(value, circle[f'scale_{axis}_um_per_px']),
                    scope='Only this grid axis has observed hierarchy; NOT a third complete consensus method'))
    if all('pitch_minor_baseline_px' in d for d in grid['axes'].values()):
        findings['grid_geometric_anisotropy_proxy'] = {
            family: percent_difference(1/grid['axes']['x'][f'pitch_{family}_baseline_px'],
                                       1/grid['axes']['y'][f'pitch_{family}_baseline_px'])
            for family in ('minor', 'major')}
        findings['grid_geometric_anisotropy_caveat'] = 'Assumes equal nominal divisions on both axes; dimensionless geometry proxy, not identified physical sx/sy.'
    if 150 in by_diameter and 70 in by_diameter:
        a, b = by_diameter[150], by_diameter[70]
        findings['circle_discrepancy'] = {}
        for axis in ('x', 'y'):
            key = f'scale_{axis}_um_per_px'
            va = [r[key] for r in sensitivity[a['source_file']]['experiments'] if r['status'] == 'MEASURED']
            vb = [r[key] for r in sensitivity[b['source_file']]['experiments'] if r['status'] == 'MEASURED']
            differences = [percent_difference(x, y) for x in va for y in vb]
            findings['circle_discrepancy'][axis] = dict(
                baseline_difference_percent=percent_difference(a[key], b[key]),
                sensitivity_pairwise_min_percent=min(differences), sensitivity_pairwise_max_percent=max(differences),
                c70_total_diameter_delta_to_match_c150_px=70/a[key]-b['fit_metrics'][f'diameter_{axis}_px'])
        findings['circle_discrepancy_caveat'] = 'Counterfactual equality only: C150 is not assumed ground truth and no diameter is corrected.'
    return findings


def write_report(summary, output):
    grid=summary['grid']; lines=['# 18S-A.1 — scientific review','',
        '**PROVISIONAL_ONLY — not a validated physical calibration.**','',
        'Reference pattern tolerance: **UNKNOWN**. No metrological uncertainty assigned.', '',
        'Baseline numerical results reproduced exactly before the experiments.', '', '## Grid hierarchy','',
        f"Overall: **{grid['status']}**. Rotation {grid['estimated_rotation_deg']:.12f} degrees.", '',
        grid['interpretation_policy'], '',
        table(['Axis','minor pitch px','major pitch px','ratio','abs deviation from 5','deviation %','short/long marks','observed 5-interval groups','phase RMS px'],
        [[axis,d['pitch_minor_baseline_px'],d['pitch_major_baseline_px'],d['ratio'],d['absolute_deviation_from_5'],d['percent_deviation_from_5'],
          f"{d.get('n_minor')}/{d.get('n_major')}",d.get('complete_observed_groups'),d.get('major_minor_phase_rms_px')] for axis,d in grid['axes'].items()]),'']
    for axis,d in grid['axes'].items():
        lines += [f'### Axis {axis}', '',f"Status: {d['geometry_status']}; reason: {d.get('reason','observed hierarchy')}", '',
            table(['position px','index (zero at first observed mark)','type','residual px','accepted'],
                  [[m['position_px'],m['index'],m['kind'],m['residual_px'],m['accepted']] for m in d.get('marks',[])]),'',
            f"Minor scale: {d['scale_minor_um_per_px']}; major scale: {d['scale_major_um_per_px']} µm/px.",
            f"Self consistency: {d.get('self_consistency_absolute_um_per_px')} µm/px; {d.get('self_consistency_symmetric_percent')} %.", '',
            'Missing indices are inferred, not observed. Short/long family fits and all groups are retained in JSON.', '',
            'Spatial variation (descriptive, includes edge-sensitive marks):', '',
            '```json',json.dumps(d.get('spatial_variation'),indent=2),'```','',
            table(['family','pitch before','pitch after','RMS before','RMS after','pitch change %'],
                [[r['family'],r['before_rotation']['pitch_px'] if r['before_rotation'] else None,r['after_rotation']['pitch_px'],
                  r['before_rotation']['residual_px'] if r['before_rotation'] else None,r['after_rotation']['residual_px'],r['pitch_change_percent']]
                 for r in d['rotation_comparison']]),'',
            'Rotation comparison on identical marks (exclude set-change confounding):','',
            '```json',json.dumps(d.get('rotation_common_marks'),indent=2),'```','']
    lines += ['## Patterns and consensus','',table(['Method','sx µm/px','sy µm/px','anisotropy %','status'],
        [[r['source_file'],r['scale_x_um_per_px'],r['scale_y_um_per_px'],r['anisotropy_percent'],r['measurement_status']] for r in summary['review_methods']]),'',
        table(['Comparison','difference X %','difference Y %'],
              [['GRID vs C150', 'N/A' if grid['grid_scale_x'] is None else 'see consensus','N/A' if grid['grid_scale_y'] is None else 'see consensus'],
               ['GRID vs C70', 'N/A' if grid['grid_scale_x'] is None else 'see consensus','N/A' if grid['grid_scale_y'] is None else 'see consensus']]+
              [[' vs '.join(p['sources']),p['difference_x_percent'],p['difference_y_percent']] for p in summary['consensus_statistics']['pairwise']]),'',
        '```json',json.dumps(summary['consensus_statistics'],indent=2),'```','',
        f"Auxiliary isotropic mean: {summary['provisional_isotropic_scale']} µm/px (AUXILIARY / PROVISIONAL).",'',
        '## Circle sensitivity','',
        'Same one-factor perturbations for both images. Sample dispersion across settings is algorithmic sensitivity, not independent replicates or measurement uncertainty.','']
    for name,data in summary['algorithmic_sensitivity'].items():
        lines += [f'### {name}','',table(['Experiment','status','Dx px','Dy px','sx','sy','RMS px','inliers'],
            [[r['experiment'],r['status'],r.get('diameter_x_px'),r.get('diameter_y_px'),r.get('scale_x_um_per_px'),r.get('scale_y_um_per_px'),r.get('fit_residual_px'),r.get('inlier_fraction')]
             for r in data['experiments']]),'','```json',json.dumps(data['summaries'],indent=2),'```','']
        for axis,rows in summary['diameter_perturbations'][name].items():
            lines += [f'Total diameter perturbation, axis {axis}; not a radial displacement of each edge.','',
                      table(['diameter delta px','diameter px','scale','scale delta','scale change %'],
                            [[r[k] for k in ('diameter_delta_px','diameter_px','scale_um_per_px','scale_delta_um_per_px','scale_change_percent')] for r in rows]),'']
    lines += ['## Quantitative interpretation (no corrections)','',
              '```json',json.dumps(summary['scientific_findings'],indent=2),'```','',
              '## Limitations','']+['- '+text for text in summary['limitations']]
    (output/'report.md').write_text('\n'.join(lines)+'\n')


def run(manifest, baseline_file, output):
    manifest,baseline_file,output=Path(manifest).resolve(),Path(baseline_file).resolve(),Path(output).resolve()
    entries=json.loads(manifest.read_text()); expected=json.loads(baseline_file.read_text())['results']
    sources=[(manifest.parent/e['file']).resolve() for e in entries]
    if any(p.is_relative_to(output) for p in sources) or baseline_file == output/'results.json':
        raise ValueError('Output cannot overwrite sources or baseline')
    if len(entries)!=3 or [e['pattern_type'] for e in entries]!=['graduated_grid','circle','circle']:
        raise ValueError('Study requires one grid followed by two circle references')
    if len(set(sources)) != 3:
        raise ValueError('Study requires three distinct source files')
    fresh=[]
    for source,entry,old in zip(sources,entries,expected):
        result=measure_image(source,entry)
        old={k:v for k,v in old.items() if k!='diagnostic_file'}
        if json.loads(json.dumps(result)) != old:
            raise ValueError('BASELINE_CALIBRATION_REGRESSION')
        fresh.append(result)
    if len(fresh)!=3:
        raise ValueError('BASELINE_CALIBRATION_REGRESSION')
    output.mkdir(parents=True,exist_ok=True)
    with Image.open(sources[0]) as image:
        grid=review_grid(np.asarray(image.convert('L')),fresh[0])
    # Freeze the grid interpretation before processing any circle perturbation.
    (output/'grid-evidence.json').write_text(json.dumps(grid,indent=2,allow_nan=False)+'\n')
    grid_diagrams(sources[0],grid,output)
    methods=[dict(r) for r in fresh]
    if grid['status']=='GEOMETRICALLY_IDENTIFIED_PROVISIONAL':
        methods[0].update(scales(grid['grid_scale_x'],grid['grid_scale_y']))
        methods[0]['measurement_status']='MEASURED'
    sensitivity={};diameter={}
    for index in (1,2):
        result=fresh[index];name=result['source_file'];d=result['known_dimension_um']
        with Image.open(sources[index]) as image:
            sensitivity[name]=circle_sensitivity(np.asarray(image.convert('L')),d)
        b=sensitivity[name]['experiments'][0]
        for axis in ('x','y'):
            if b.get(f'scale_{axis}_um_per_px') != result[f'scale_{axis}_um_per_px']:
                raise ValueError('BASELINE_CALIBRATION_REGRESSION')
        diameter[name]={axis:diameter_perturbation(result['fit_metrics'][f'diameter_{axis}_px'],d) for axis in ('x','y')}
        save_diagnostic(sources[index],result,output/f'circle-{index}-diagnostic.png')
    combined=consensus(methods)
    for axis in ('x','y'):
        s=combined['statistics'][axis];s['relative_range_percent']=100*(s['max']-s['min'])/s['mean']
    summary=dict(scientific_status='PROVISIONAL_ONLY',baseline_reproduced_exactly=True,
        reference_pattern_tolerance='UNKNOWN',grid_interpretation=grid['status'],grid=grid,
        grid_scale_x=grid['grid_scale_x'],grid_scale_y=grid['grid_scale_y'],
        review_methods=methods,consensus_statistics=combined,
        provisional_mean_scale_x=combined['statistics']['x']['mean'],
        provisional_median_scale_x=combined['statistics']['x']['median'],
        provisional_mean_scale_y=combined['statistics']['y']['mean'],
        provisional_median_scale_y=combined['statistics']['y']['median'],
        provisional_isotropic_scale=(combined['statistics']['x']['mean']+combined['statistics']['y']['mean'])/2,
        isotropic_status='AUXILIARY / PROVISIONAL',algorithmic_sensitivity=sensitivity,diameter_perturbations=diameter,
        anisotropy_analysis=[dict(source=r['source_file'],signed_xy_percent=100*(r['scale_x_um_per_px']-r['scale_y_um_per_px'])/r['mean_scale_um_per_px'],
                                 anisotropy_percent=r['anisotropy_percent'],axis_ratio=r['fit_metrics']['axis_ratio'],
                                 ellipse_angle_deg=r['fit_metrics']['ellipse_angle_deg'],fit_residual_px=r['fit_metrics']['fit_residual_px']) for r in fresh[1:]],
        limitations=['No reference certificate/tolerance or repeat acquisitions are available.',
            'Grid: missing interior marks are not measured subdivisions; no circle data select its physical family.',
            'Fit residual, algorithmic sensitivity and between-pattern dispersion are distinct from metrological uncertainty.',
            'No physical inference from DPI. Original-resolution measurements; no source resize.',
            'Spatial trends are descriptive, can include extraction/clipping/pattern effects and do not establish optical distortion.',
            'No final PASS/REVIEW/FAIL thresholds or automatic physical conversions are introduced.'])
    summary['scientific_findings'] = scientific_findings(grid, fresh[1:], sensitivity)
    for source,r in zip(sources,fresh):
        if hashlib.sha256(source.read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('SOURCE_CHANGED_DURING_STUDY')
    summary['original_hashes_unchanged']=True
    (output/'results.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    write_report(summary,output)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',required=True);parser.add_argument('--baseline',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();r=run(args.manifest,args.baseline,args.output)
    print(json.dumps({'baseline_exact':r['baseline_reproduced_exactly'],'grid':r['grid_interpretation'],
                      'consensus':r['consensus_statistics']['status'],'original_hashes_unchanged':r['original_hashes_unchanged']},indent=2))


if __name__=='__main__':
    main()
