"""Apresentação PDF de 10 páginas baseada nos outputs salvos do notebook."""
from pathlib import Path
import json,base64,io
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/pdf/apresentacao_oonca_institucional.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
nb=json.loads((ROOT/'notebooks/entregavel_datathon_fgv.ipynb').read_text())
pdfmetrics.registerFont(TTFont('Sans','/usr/share/fonts/liberation/LiberationSans-Regular.ttf'))
pdfmetrics.registerFont(TTFont('Sans-Bold','/usr/share/fonts/liberation/LiberationSans-Bold.ttf'))
W,H=960,540
BG='#FFFFFF'; INK='#18212B'; GREEN='#344659'; DARK='#1D2733'; LIME='#FFFFFF'; MUTED='#626A73'
c=canvas.Canvas(str(OUT),pagesize=(W,H))
c.setTitle('OONCA - 7º Datathon de Moedas Digitais FGV - Grupo 6')
c.setAuthor('Grupo 6')
c.setSubject('Governança pré-assinatura e monitoramento de operações on-chain')

def text(s,x,y,w=850,size=18,color=INK,bold=False,leading=None):
 st=ParagraphStyle('t',fontName='Sans-Bold' if bold else 'Sans',fontSize=size,leading=leading or size*1.27,textColor=HexColor(color))
 p=Paragraph(s,st); aw,ah=p.wrap(w,1000)
 assert y+ah<528, (s,y,ah)
 p.drawOn(c,x,H-y-ah)
 return ah

def base(n,title=None,sub=None,dark=False,source=None):
 c.setFillColor(HexColor(DARK if dark else BG));c.rect(0,0,W,H,fill=1,stroke=0)
 text('OONCA',48,25,200,12,LIME if dark else GREEN,True)
 text(f'GRUPO 6    /    {n:02d}',772,25,145,10,'#B9C1CB' if dark else MUTED)
 if title: text(title,48,70,864,32,'#FFFFFF' if dark else INK,True)
 if sub: text(sub,48,119,860,16,'#D5D9DF' if dark else MUTED)
 text(source or '7º Datathon de Moedas Digitais FGV',48,508,860,9,'#B9C1CB' if dark else MUTED)

def end():c.showPage()
def image(cell,x,y,w,h):
 out=next(o for o in nb['cells'][cell]['outputs'] if 'image/png' in o.get('data',{}))
 b=base64.b64decode(''.join(out['data']['image/png']))
 img=ImageReader(io.BytesIO(b));iw,ih=img.getSize();r=min(w/iw,h/ih)
 c.drawImage(img,x+(w-iw*r)/2,H-y-ih*r,width=iw*r,height=ih*r)

def metric(v,label,x,y,w=250,detail=None):
 text(v,x,y,w,44,GREEN,True)
 text(label,x,y+58,w,18,INK,True)
 if detail:text(detail,x,y+88,w,15,MUTED)

def item(head,body,x,y,w=400):
 text(head,x,y,w,21,GREEN,True)
 text(body,x,y+36,w,18,INK)

# 1
base(1,dark=False)
text('OONCA',48,112,850,64,INK,True)
text('Risco e governança<br/>de operações on-chain',50,214,820,38,INK,True)
text('Operador On-Chain com Apoio de IA',52,344,820,23,INK)
text('Risco comportamental e responsabilização<br/>em operações on-chain',52,391,820,19,MUTED)
end()
# 2
base(2,'Governança antes da assinatura','O histórico registra a operação. O OONCA acrescenta política e responsabilidade.')
for y,num,head,body in [
(174,'01','Contexto da carteira','Histórico deduplicado, contraparte e corte temporal.'),
(250,'02','Política de risco','Regras explícitas geram APPROVE, REVIEW ou BLOCK.'),
(326,'03','Registro de auditoria','Motivos, operador, política e hash SHA-256 das evidências.')]:
 text(num,48,y,60,31,GREEN,True);text(head,125,y,775,23,INK,True);text(body,125,y+33,775,18,MUTED)
text('Modo read-only: o agente não assina nem transmite transações.',48,434,865,20,GREEN,True)
text('Na execução salva, use_llm=False. As explicações também são determinísticas.',48,471,850,15,MUTED)
end()
# 3
base(3,'Integridade da amostra e metadados','1.803 linhas brutas, 1.745 transações únicas e 30 carteiras remetentes.',source='Fonte: diagnóstico salvo do notebook. Amostra sintética calibrada e reprodutível, janeiro a agosto de 2017.')
image(4,36,156,888,292)
text('58 linhas repetidas (3,22%) exigem deduplicação na cadência.',48,455,850,21,GREEN,True)
text('Os 60 endereços catalogados não implicam cobertura de todas as contrapartes.',48,484,850,15,MUTED)
end()
# 4
base(4,'Valores assimétricos e concentração de falhas','A média de 2,1458 ETH supera a mediana de 1,0922 ETH na amostra.',source='Fonte: distribuições salvas do notebook, amostra sintética. Estatísticas de valor calculadas sobre as linhas brutas.')
image(6,36,154,888,291)
text('A triagem compara o valor ao P95 da própria carteira.',48,451,850,21,GREEN,True)
text('A avaliação da taxa de erro exige pelo menos 20 observações.',48,481,850,17,MUTED)
end()
# 5
base(5,'Sinais comportamentais de automação','Cadência sub-minuto, dispersão horária, rajadas e concentração de destinatários.',source='Fonte: notebook, features das 30 carteiras. Proxy comportamental não identifica autoria por IA ou fraude.')
image(9,36,156,888,284)
text('23 de 30 carteiras acionaram ao menos um proxy.',48,449,850,21,GREEN,True)
text('Carteiras esporádicas também acionam a entropia. Falta validar falsos positivos.',48,482,850,16,MUTED)
end()
# 6
base(6,'Pontuação nos cinco cenários operacionais','Revisão a partir de 30 pontos. O teto de 100 ETH causa bloqueio determinístico.',source='Fonte: batch_analyze salvo. Score heurístico de 0 a 100, sem interpretação probabilística.')
labels=['Rotina conhecida / 0,5 ETH','Novo contrato / 25 ETH','Proxy de automação / 5 ETH','Sem histórico / 1 ETH','Acima do teto / 150 ETH']
values=[15,60,40,60,100]; decisions=['APPROVE','REVIEW','REVIEW','REVIEW','BLOCK']
colors=['#287B70','#B78022','#B78022','#B78022','#AF3C3C']
x0=345; chartw=405
for j,(label,val,dec,col) in enumerate(zip(labels,values,decisions,colors)):
 y=179+j*53
 text(label,48,y+4,285,17)
 c.setFillColor(HexColor('#EBEDF0'));c.rect(x0,H-y-30,chartw,30,stroke=0,fill=1)
 c.setFillColor(HexColor(col));c.rect(x0,H-y-30,chartw*val/100,30,stroke=0,fill=1)
 text(str(val),x0+chartw*val/100+7,y+4,48,16,INK,True)
 text(dec,806,y+5,110,15,col,True)
c.setStrokeColor(HexColor(INK));c.setDash(4,3);c.line(x0+chartw*.3,H-170,x0+chartw*.3,H-429);c.setDash()
text('Limiar 30',x0+chartw*.3-36,440,110,13,MUTED)
text('Uma aprovação, três revisões humanas e um bloqueio na triagem.',48,477,850,18,GREEN,True)
end()
# 7
base(7,'Caso de 25 ETH: evidências da revisão','REVIEW, com 60 pontos. As regras mostram por que a operação exige atenção.',source='Fonte: painel de evidências salvo do cenário 2. Gráficos recompostos com os valores exibidos no notebook.')
text('Contribuição de cada regra',48,164,420,20,GREEN,True)
text('Valor proposto e histórico (ETH)',520,164,390,20,GREEN,True)
for j,(lab,val) in enumerate([('Destino inédito',15),('Valor > 2 × P95',20),('Proxy de automação',15),('Destinatário contrato',10)]):
 y=211+j*49
 text(lab,48,y,193,16)
 c.setFillColor(HexColor('#B78022'));c.rect(243,H-y-24,val/20*160,24,stroke=0,fill=1)
 text(f'+{val}',243+val/20*160+8,y,52,16,INK,True)
for j,(lab,val,fmt,col) in enumerate([('Proposto',25,'25', '#B78022'),('2 × P95',3.0798,'3,0798','#287B70'),('P95',1.5399,'1,5399','#287B70'),('Mediana',.7322,'0,7322','#287B70')]):
 y=211+j*49
 text(lab,520,y,105,16)
 c.setFillColor(HexColor(col));c.rect(630,H-y-24,val/25*197,24,stroke=0,fill=1)
 text(fmt,630+val/25*197+8,y,75,15,INK,True)
text('Reduzir para 3,0798 ETH trata apenas a regra de valor.',48,438,850,22,GREEN,True)
text('A contraparte, a capacidade de receber ETH e a responsabilidade ainda exigem verificação.',48,478,850,17,MUTED)
end()
# 8
base(8,'Completude observada da auditoria','Percentual de campos presentes na métrica das cinco operações avaliadas.',source='Fonte: accountability_score e JSON salvos. O quadro conceitual de 100% usa campos distintos.')
for y,lab,val,detail in [(191,'Quatro operações',8/9,'8 de 9 campos / 88,89%'),(285,'Sem histórico',6/9,'6 de 9 campos / 66,67%')]:
 text(lab,48,y,230,20,INK,True)
 c.setFillColor(HexColor('#E8EBEF'));c.rect(289,H-y-32,590,32,stroke=0,fill=1)
 c.setFillColor(HexColor('#287B70'));c.rect(289,H-y-32,590*val,32,stroke=0,fill=1)
 text(detail,289,y+42,590,18,GREEN,True)
text('SHA-256 permite verificar alterações nas evidências.',48,398,850,24,GREEN,True)
text('O hash depende de uma referência confiável. Ele não torna o armazenamento imutável nem garante a veracidade dos dados.',48,446,850,18,MUTED)
end()
# 9
base(9,'Reversões de mercado: histórico e simulação','O alerta diário oferece contexto separado da triagem pré-assinatura.',source='Fonte: seção de mercado do notebook. DOGE: eventos retrospectivos. DEMO: cenário fictício, sem comprovação preditiva.')
image(19,30,156,620,331)
text('Regra diária',675,163,235,19,GREEN,True)
text('Alta ≥ 15% e volume ≥ 2 × a mediana de 30 dias.',675,196,235,17)
text('Reversão: queda ≥ 15% em um dos três fechamentos seguintes.',675,251,235,17)
text('Simulação DEMO',675,324,235,19,GREEN,True)
text('+50% e volume 7 ×.<br/>Score 0,239 > limiar 0,002.<br/>Queda posterior de 24%.',675,358,235,17)
text('Sem métricas de holdout<br/>exibidas nesta seção.',675,444,235,15,MUTED)
end()
# 10
base(10,'Síntese e agenda de validação',dark=False)
text('O protótipo reúne política e evidências<br/>antes da assinatura.',48,150,850,30,INK,True)
text('Entrega demonstrada',48,255,410,23,INK,True)
text('Triagem explicável em cinco cenários.<br/>Recomendações para revisão humana.<br/>Registro de responsabilidade e hash.<br/>Alerta diário de contexto de mercado.',48,300,410,19,MUTED)
text('Validação necessária',510,255,400,23,INK,True)
text('Generalização em dados on-chain reais.<br/>Falsos positivos dos proxies.<br/>Cobertura e temporalidade dos metadados.<br/>Calibração e desempenho fora da amostra.',510,300,400,19,MUTED)
text('Notebook e relatório HTML acompanham a análise detalhada e a reprodução.',48,454,864,18,MUTED)
end()
c.save()
print(OUT)
