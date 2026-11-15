from wiki import query
for q,t in [('Q01','深偽 仿聲 基本概念'),('Q02','香港 臺中 案例'),('Q03','親友 聲音 回撥'),('Q04','TikTok Instagram LINE 標示 帳號'),('Q05','查證 165 證據'),('Q06','勒索 認證碼 復原')]:
    r=query(q,t)
    print(q,len(r['pages']),'pages',len(r['claims']),'claims')
