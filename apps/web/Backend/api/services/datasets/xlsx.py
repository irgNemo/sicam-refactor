"""Small values-only OOXML writer; standard library, no formulas or shared strings."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree.ElementTree import Element, SubElement, tostring

S='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P='http://schemas.openxmlformats.org/package/2006/relationships'
C='http://schemas.openxmlformats.org/package/2006/content-types'


def col(index):
    result=''
    while index:index,remainder=divmod(index-1,26);result=chr(65+remainder)+result
    return result


def workbook(sheets):
    output=BytesIO()
    with ZipFile(output,'w',ZIP_DEFLATED) as archive:
        def put(name,node):archive.writestr(name,tostring(node,encoding='utf-8',xml_declaration=True))
        types=Element('Types',xmlns=C)
        SubElement(types,'Default',Extension='rels',ContentType='application/vnd.openxmlformats-package.relationships+xml')
        SubElement(types,'Default',Extension='xml',ContentType='application/xml')
        SubElement(types,'Override',PartName='/xl/workbook.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml')
        root=Element('Relationships',xmlns=P);SubElement(root,'Relationship',Id='rId1',Type=R+'/officeDocument',Target='xl/workbook.xml');put('_rels/.rels',root)
        book=Element('workbook',xmlns=S);items=SubElement(book,'sheets');links=Element('Relationships',xmlns=P)
        SubElement(types,'Override',PartName='/xl/styles.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml')
        SubElement(links,'Relationship',Id='styles',Type=R+'/styles',Target='styles.xml')
        styles=Element('styleSheet',xmlns=S)
        fonts=SubElement(styles,'fonts',count='2')
        SubElement(fonts,'font');SubElement(SubElement(fonts,'font'),'b')
        fills=SubElement(styles,'fills',count='2')
        SubElement(SubElement(fills,'fill'),'patternFill',patternType='none')
        SubElement(SubElement(fills,'fill'),'patternFill',patternType='gray125')
        SubElement(SubElement(styles,'borders',count='1'),'border')
        base=SubElement(styles,'cellStyleXfs',count='1');SubElement(base,'xf',numFmtId='0',fontId='0',fillId='0',borderId='0')
        formats=SubElement(styles,'cellXfs',count='2')
        for font_id in ('0','1'):
            SubElement(formats,'xf',numFmtId='0',fontId=font_id,fillId='0',borderId='0',xfId='0',applyFont='1')
        put('xl/styles.xml',styles)
        for i,(name,headers,rows) in enumerate(sheets,1):
            SubElement(items,'sheet',name=name,sheetId=str(i),attrib={'{'+R+'}id':f'rId{i}'})
            SubElement(links,'Relationship',Id=f'rId{i}',Type=R+'/worksheet',Target=f'worksheets/sheet{i}.xml')
            SubElement(types,'Override',PartName=f'/xl/worksheets/sheet{i}.xml',ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml')
            sheet=Element('worksheet',xmlns=S)
            views=SubElement(sheet,'sheetViews');view=SubElement(views,'sheetView',workbookViewId='0')
            SubElement(view,'pane',ySplit='1',topLeftCell='A2',activePane='bottomLeft',state='frozen')
            widths=SubElement(sheet,'cols')
            for ci,header in enumerate(headers,1):
                typical=max((len(str(row[ci-1])) for row in rows[:200] if row[ci-1] is not None),default=0)
                width=min(48,max(12,len(str(header))+2,min(typical+2,40)))
                SubElement(widths,'col',min=str(ci),max=str(ci),width=str(width),customWidth='1')
            data=SubElement(sheet,'sheetData')
            for ri,values in enumerate([headers,*rows],1):
                row=SubElement(data,'row',r=str(ri))
                for ci,value in enumerate(values,1):
                    if value is None:continue
                    cell=SubElement(row,'c',r=f'{col(ci)}{ri}')
                    if ri==1:cell.set('s','1')
                    if isinstance(value,(int,float)):
                        SubElement(cell,'v').text=str(value)
                    else:
                        cell.set('t','inlineStr');node=SubElement(SubElement(cell,'is'),'t',attrib={'{http://www.w3.org/XML/1998/namespace}space':'preserve'});node.text=str(value)
            SubElement(sheet,'autoFilter',ref=f'A1:{col(len(headers))}{len(rows)+1}')
            put(f'xl/worksheets/sheet{i}.xml',sheet)
        put('xl/workbook.xml',book);put('xl/_rels/workbook.xml.rels',links);put('[Content_Types].xml',types)
    return output.getvalue()
