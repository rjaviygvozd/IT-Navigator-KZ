"""Kazakhstan IT ecosystem: selected official resources, no unverified scores or vacancies."""
CATALOG={
 'unis':[
 ('Nazarbayev University','Астана','https://nu.edu.kz','Программы и условия поступления уточняйте в приёмной комиссии.'),
 ('ЕНУ имени Л. Н. Гумилёва','Астана','https://enu.kz','Проверяйте актуальные образовательные программы.'),
 ('КБТУ','Алматы','https://kbtu.edu.kz','Технические образовательные программы.'),
 ('МУИТ (IITU)','Алматы','https://iitu.edu.kz','IT-направления и условия поступления.'),
 ('Satbayev University','Алматы','https://satbayev.university','Инженерные и технические программы.'),
 ('КИМЭП','Алматы','https://kimep.kz','Бизнес и менеджмент, уточните наличие нужной IT-программы.'),
 ('КазНУ имени аль-Фараби','Алматы','https://farabi.university','Программы и условия поступления на сайте.'),
 ('Торайгыров университет','Павлодар','https://tou.edu.kz','На сайте есть факультет Computer Science. Условия поступления уточняйте в приёмной комиссии. Источник просмотрен 26.10.2026.')
 ],
 'companies':[
 ('Kaspi.kz','Финтех, цифровые сервисы','https://job.kaspi.kz/','Вакансии и условия стажировок проверяйте в карьерном разделе.'),
 ('Kolesa Group','Цифровые платформы','https://kolesa.group/','Условия программ начала карьеры ищите на официальном сайте.'),
 ('Chocofamily','Онлайн-сервисы','https://choco.family/','Вакансии и возможность стажировок уточняйте у компании.'),
 ('Halyk Bank','Финтех и банковские технологии','https://halykbank.kz/','Информация о карьере и стажировках на официальном сайте.'),
 ('Beeline Казахстан','Телеком и цифровые продукты','https://beeline.kz/','Открытые программы уточняйте на сайте.'),
 ('Astana Hub','Экосистема стартапов','https://astanahub.com/','Каталог участников, образовательные возможности и события.')
 ],
 'grants':[
 ('Государственные образовательные гранты','https://www.gov.kz/memleket/entities/sci','Условия и конкурс зависят от года и группы программ.'),
 ('Официальная информация о ЕНТ','https://testcenter.kz/','Предметы, регистрация и пороги меняются по правилам года.'),
 ('Программы Astana Hub','https://astanahub.com/en/service/?locale=ru','Не все программы открыты школьникам; проверяйте критерии.')
 ],
 'communities':[
 ('Сообщество Astana Hub','https://astanahub.com/','Профессиональные обсуждения, анонсы и проекты.'),
 ('Учебные программы Astana Hub','https://edu.astanahub.com/','Курсы и задания, условия доступа уточняйте на платформе.')
 ],
 'events':[
 ('События Astana Hub','https://astanahub.com/','Актуальные анонсы, место, дата и регистрация на сайте.'),
 ('Олимпиады и конкурсы «Дарын»','https://daryn.kz/','Проверяйте открытые положения и возрастные категории.')
 ]
}
def categories():
    return [('🎓 Вузы','unis'),('🏢 Компании','companies'),('💰 Гранты и программы','grants'),('🤝 IT-сообщества','communities'),('🏆 События','events')]
def rows(key,city='Все'):
    data=CATALOG[key]
    if key=='unis' and city!='Все':
        data=[r for r in data if r[1]==city]
    return data

# The filters are exploratory themes, NOT verified university degree offerings.
PROFILE_HINTS={
 'code':['Nazarbayev University','КБТУ','МУИТ (IITU)','Satbayev University','КазНУ имени аль-Фараби'],
 'data':['Nazarbayev University','КБТУ','МУИТ (IITU)','Satbayev University','ЕНУ имени Л. Н. Гумилёва'],
 'people':['КИМЭП','КБТУ','Nazarbayev University','КазНУ имени аль-Фараби'],
 'design':['МУИТ (IITU)','Satbayev University','КазНУ имени аль-Фараби']
}
def suggested_universities(track):
    names=PROFILE_HINTS.get(track,[])
    return [r for r in CATALOG['unis'] if r[0] in names]
def university(index):
    return CATALOG['unis'][index] if isinstance(index,int) and 0<=index<len(CATALOG['unis']) else None

# Exploratory categories, not claims about currently open jobs.
COMPANY_PROFILES={
 'code':['Kaspi.kz','Kolesa Group','Chocofamily','Halyk Bank','Beeline Казахстан'],
 'data':['Kaspi.kz','Kolesa Group','Halyk Bank','Beeline Казахстан'],
 'people':['Kaspi.kz','Kolesa Group','Chocofamily','Astana Hub'],
 'design':['Kaspi.kz','Kolesa Group','Chocofamily']
}
# Educational skill cards, not inferred company technology stacks.
# Official learning pages checked 2026-10-26.
TECHNOLOGIES={
 'Python':('Язык программирования для автоматизации, анализа данных и приложений.','Напиши программу, которая считает среднюю оценку из списка чисел. Официальный учебник предполагает базовое знакомство с программированием.','https://docs.python.org/3/tutorial/'),
 'Java':('Язык программирования для приложений, в том числе серверных. Это отдельный язык, не JavaScript.','Начни с программы Hello World и вывода результата простого вычисления.','https://dev.java/learn/'),
 'Дизайн':('UX помогает понять удобство продукта, UI — спроектировать его интерфейс. Figma используется для макетов и прототипов.','Нарисуй экран школьного расписания и попроси одноклассника найти в нём нужный урок.','https://help.figma.com/hc/en-us/categories/360002042553-Figma-Design'),
 'Аналитика':('Работа с данными: сформулировать вопрос, проверить таблицу и объяснить вывод. pandas помогает обрабатывать таблицы в Python.','Возьми учебную таблицу без персональных данных и сравни средние значения двух групп.','https://pandas.pydata.org/docs/getting_started/index.html')
}
CAREER_RESOURCES=[
 ('Kolesa Academy','https://kolesa.group/education/academy','Страница программы обучения. Текущий набор, оплату, формат и возрастные условия нужно проверить на сайте.'),
 ('Kolesa Group — вакансии','https://kolesa.group/career/job','Направления разработки, аналитики, дизайна и продуктов. Открытые позиции могут изменяться.')
]
def companies_for_track(track):
    names=COMPANY_PROFILES.get(track,[])
    return [r for r in CATALOG['companies'] if r[0] in names]
