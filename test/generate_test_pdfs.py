"""
5종 표 PDF 자동 생성 — 우리 PDF→Word 변환 정확도 측정 fixture
1) simple_table.pdf - 단순 표 (4x5, 흰 배경, 검정 텍스트)
2) colored_header.pdf - 회색 헤더 + 흰 본문 (예약이체 스타일)
3) multi_color.pdf - 행마다 다른 색 (좋아함/나쁨/보통)
4) compact_small.pdf - 작은 글자, 좁은 셀, 많은 컬럼 (10개 컬럼)
5) wide_merged.pdf - 넓은 셀 + 부분 병합처럼 보이는 빈 셀
"""
import sys, os
from pathlib import Path
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:
    print("reportlab 설치 필요: pip install reportlab")
    sys.exit(1)

OUT = Path(__file__).parent / "fixtures" / "test_pdfs"
OUT.mkdir(parents=True, exist_ok=True)

# 한국어 폰트 등록 (Windows 시스템 폰트)
try:
    pdfmetrics.registerFont(TTFont('MalgunGothic', 'C:/Windows/Fonts/malgun.ttf'))
    KO_FONT = 'MalgunGothic'
except Exception:
    KO_FONT = 'Helvetica'

def make_simple():
    doc = SimpleDocTemplate(str(OUT/"1_simple.pdf"), pagesize=A4)
    data = [
        ['항목', '수량', '단가', '합계'],
        ['연필', '10', '500', '5,000'],
        ['지우개', '5', '1,000', '5,000'],
        ['공책', '3', '2,500', '7,500'],
        ['합계', '', '', '17,500'],
    ]
    t = Table(data, colWidths=[100, 80, 80, 100])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), KO_FONT, 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    doc.build([t])

def make_colored_header():
    doc = SimpleDocTemplate(str(OUT/"2_colored_header.pdf"), pagesize=A4)
    data = [
        ['No.', '날짜', '거래처', '금액(원)'],
        ['1', '2026.01.05', '솔박스', '1,500,000'],
        ['2', '2026.01.10', '카카오', '2,300,000'],
        ['3', '2026.01.15', '네이버', '1,800,000'],
        ['4', '2026.01.20', 'KT', '950,000'],
        ['합계', '', '', '6,550,000'],
    ]
    t = Table(data, colWidths=[60, 100, 120, 120])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), KO_FONT, 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#888888')),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#DEDEDE')),
        ('FONTNAME', (0,0), (-1,0), KO_FONT),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#222222')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    doc.build([t])

def make_multi_color():
    doc = SimpleDocTemplate(str(OUT/"3_multi_color.pdf"), pagesize=A4)
    data = [
        ['상태', '제품명', '수량', '평가'],
        ['양호', '제품 A', '120', '★★★★★'],
        ['주의', '제품 B', '85', '★★★'],
        ['긴급', '제품 C', '20', '★'],
        ['양호', '제품 D', '150', '★★★★'],
    ]
    t = Table(data, colWidths=[80, 120, 80, 120])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), KO_FONT, 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#3B5BAB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#E8F5E9')),  # 양호 - 초록
        ('BACKGROUND', (0,2), (-1,2), colors.HexColor('#FFF3E0')),  # 주의 - 주황
        ('BACKGROUND', (0,3), (-1,3), colors.HexColor('#FFEBEE')),  # 긴급 - 빨강
        ('BACKGROUND', (0,4), (-1,4), colors.HexColor('#E8F5E9')),  # 양호 - 초록
        ('TEXTCOLOR', (0,3), (0,3), colors.HexColor('#C62828')),  # 긴급 행 글자 빨강
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    doc.build([t])

def make_compact_small():
    doc = SimpleDocTemplate(str(OUT/"4_compact.pdf"), pagesize=A4)
    data = [
        ['ID','이름','부서','직급','입사','전화','이메일','연봉(만원)','평가','비고'],
        ['001','김철수','개발1팀','과장','2020.03','010-1234-5678','kim@a.co','7500','A','우수'],
        ['002','이영희','개발2팀','대리','2021.07','010-2345-6789','lee@b.co','5800','B+','평균'],
        ['003','박민수','기획팀','차장','2018.10','010-3456-7890','park@c.co','8200','S','특별'],
        ['004','최지원','영업팀','사원','2023.04','010-4567-8901','choi@d.co','4200','B','양호'],
        ['005','정한솔','경영팀','부장','2015.01','010-5678-9012','jeong@e.co','9500','A+','우수'],
    ]
    t = Table(data, colWidths=[35,55,60,40,50,80,80,55,30,40])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), KO_FONT, 7),
        ('GRID', (0,0), (-1,-1), 0.3, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    doc.build([t])

def make_wide_merged():
    doc = SimpleDocTemplate(str(OUT/"5_wide.pdf"), pagesize=A4)
    data = [
        ['프로젝트', '담당자', '시작', '종료', '상태'],
        ['오픈소스 멀티모달 AI 기반 방송 콘텐츠', '신현식', '2024.06', '2026.05', '진행중'],
        ['', '', '', '', ''],  # 빈 행 (빈 셀 처리)
        ['', '김주홍', '2024.06', '2025.12', '완료'],  # 부분 빈 셀 (병합처럼)
        ['CDN 인프라 구축 사업', '이종필', '2025.01', '2026.06', '진행중'],
    ]
    t = Table(data, colWidths=[200, 80, 80, 80, 80])
    t.setStyle(TableStyle([
        ('FONT', (0,0), (-1,-1), KO_FONT, 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    doc.build([t])

if __name__ == '__main__':
    make_simple()
    make_colored_header()
    make_multi_color()
    make_compact_small()
    make_wide_merged()
    files = sorted(OUT.glob("*.pdf"))
    print(f"✅ {len(files)}개 PDF 생성됨:")
    for f in files:
        print(f"  {f.name} ({f.stat().st_size} bytes)")
