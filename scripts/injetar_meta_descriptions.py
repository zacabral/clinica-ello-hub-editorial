#!/usr/bin/env python3
"""
Script de Injeção em Lote de Meta Descriptions e Palavras-Chave Foco (Yoast SEO)
Site: https://drisaiascabral.com.br
Ambiente: Clínica Ello 2027 — Diretoria Digital (DIR-07)
"""

import urllib.request
import json
import base64
import re
import html
import time
import os

WP_URL = os.environ.get('WP_URL', 'https://drisaiascabral.com.br')
WP_USER = os.environ.get('WP_USER', 'gerente-redacao.editorial')
WP_APP_PASS = os.environ.get('WP_APP_PASS', '')

auth = base64.b64encode(f'{WP_USER}:{WP_APP_PASS}'.encode('utf-8')).decode('utf-8')
headers = {
    'Authorization': f'Basic {auth}',
    'Content-Type': 'application/json',
    'User-Agent': 'Clínica-Ello-Editorial/1.0'
}

def clean_html(raw_html):
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = html.unescape(text)
    text = re.sub(r'\[&hellip;\]', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_focus_kw(title):
    t = clean_html(title).lower()
    t = re.sub(r'\s*\|\s*.*$', '', t)
    t = re.sub(r'\s*&#8211;\s*.*$', '', t)
    t = re.sub(r'\s*-\s*dr.*$', '', t)
    t = re.sub(r'\s*-\s*cirurgi.*$', '', t)
    t = re.sub(r':.*$', '', t) # remove colon subtitle
    t = re.sub(r'\?.*$', '', t)
    t = t.strip()
    # take up to 4 words
    words = t.split()
    return ' '.join(words[:4]) if words else 'cirurgia plástica'

def generate_meta_description(title, excerpt, content):
    t_clean = clean_html(title)
    t_clean = re.sub(r'\s*\|\s*.*$', '', t_clean)
    t_clean = re.sub(r'\s*&#8211;\s*.*$', '', t_clean)
    t_clean = re.sub(r'\s*-\s*Dr.*$', '', t_clean).strip()
    
    text = clean_html(excerpt) if excerpt else clean_html(content[:600])
    
    # Try finding first sentence
    sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 20]
    first_sent = sentences[0] if sentences else ''
    
    if first_sent and len(first_sent) <= 90:
        desc = f'{first_sent}. Saiba mais com o Dr. Isaias Cabral.'
    elif first_sent and len(first_sent) <= 120:
        desc = f'{first_sent}. Dr. Isaias Cabral.'
    else:
        desc = f'Entenda tudo sobre {t_clean.lower()}, indicações anatômicas e cuidados pré e pós-operatórios com o Dr. Isaias Cabral.'

    # Adjust length between 140 and 158 chars
    if len(desc) > 158:
        desc = desc[:154].rstrip() + '...'
    if len(desc) < 130:
        desc = desc.rstrip('.') + f' — Cirurgião Plástico em Governador Valadares.'
        if len(desc) > 158:
            desc = desc[:154].rstrip() + '...'

    return desc

def main():
    print('=== INICIANDO INJEÇÃO DE META DESCRIPTIONS EM LOTE ===')
    page = 1
    total_updated = 0
    total_skipped = 0
    errors = 0

    while True:
        url = f'{WP_URL}/wp-json/wp/v2/posts?per_page=50&page={page}'
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                posts = json.loads(resp.read().decode('utf-8'))
                if not posts:
                    break
                
                print(f'Lendo página {page} ({len(posts)} posts)...')
                for p in posts:
                    post_id = p['id']
                    meta = p.get('meta', {})
                    current_desc = meta.get('_yoast_wpseo_metadesc')
                    
                    if current_desc and len(current_desc) > 20 and not current_desc.startswith('A abdominoplastia em âncora é o tipo'):
                        total_skipped += 1
                        continue

                    title = p['title']['rendered']
                    excerpt = p.get('excerpt', {}).get('rendered', '')
                    content = p.get('content', {}).get('rendered', '')
                    
                    meta_desc = generate_meta_description(title, excerpt, content)
                    focus_kw = extract_focus_kw(title)
                    
                    update_url = f'{WP_URL}/wp-json/wp/v2/posts/{post_id}'
                    payload = {
                        'meta': {
                            '_yoast_wpseo_metadesc': meta_desc,
                            '_yoast_wpseo_focuskw': focus_kw
                        }
                    }
                    
                    up_req = urllib.request.Request(
                        update_url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers=headers,
                        method='POST'
                    )
                    try:
                        with urllib.request.urlopen(up_req) as up_resp:
                            total_updated += 1
                            if total_updated % 10 == 0:
                                print(f'Atualizados {total_updated} posts... (Último: #{post_id} - {title[:30]})')
                    except Exception as err:
                        print(f'Erro ao atualizar post #{post_id}:', err)
                        errors += 1
                    
                    time.sleep(0.3) # Rate limit suave para não sobrecarregar o LiteSpeed
                
                total_pages = int(resp.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                page += 1
        except Exception as e:
            print(f'Erro na leitura da página {page}:', e)
            break

    print(f'\n=== CONCLUÍDO! ===')
    print(f'Total de posts atualizados com Meta Description: {total_updated}')
    print(f'Total de posts já otimizados/ignorados: {total_skipped}')
    print(f'Erros: {errors}')

if __name__ == '__main__':
    main()
