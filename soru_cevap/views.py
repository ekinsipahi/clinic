"""
soru_cevap/views.py — v6 FIXED
Düzeltmeler:
  - UserBehavior.log() kaldırıldı → doğru metodlara yönlendirildi:
      record_view(), record_like(), record_comment(), record_question(), record_time()
  - UserBehavior.get_recommended_articles() kaldırıldı → RecommendationEngine.recommend_articles()
  - sure_takip: JSON body parse, UserBehavior.record_time() düzgün çağrı
  - article_page context: 'track_article_id' ve 'track_url' eklendi
    (template JS'de data-* attribute olarak kullanılır, {{ }} tag DEĞİL)
"""

import json as json_lib

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.db.models import F, Avg, Case, When, IntegerField, Count, Q
from django.utils import translation
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db.models import Count as DjCount

from soru_cevap.ai_moderation import auto_moderate

from .models import (
    Article, Question, Comment, Like, build_comment_tree,
    QuestionLike, UserBehavior, RecommendationEngine, ArticleTag,
)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _lang(request) -> str:
    ns = getattr(getattr(request, 'resolver_match', None), 'namespace', 'tr-qa')
    return 'en' if ns == 'en-qa' else 'tr'


def _qa_prefix(language: str) -> str:
    return '/question-and-answer' if language == 'en' else '/soru-cevap'


def _activate_language(language: str):
    translation.activate(language)


def _ensure_session(request) -> str:
    """
    Login olmuş kullanıcı için sabit 'user_<pk>' key döner.
    Böylece farklı cihaz/tarayıcıdan giriş yapsa bile
    davranış verileri aynı bucket'ta birikir.
    """
    if request.user.is_authenticated:
        return f"user_{request.user.pk}"
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _base_ctx(request) -> dict:
    lang = _lang(request)
    _activate_language(lang)
    return {'language': lang, 'qa_prefix': _qa_prefix(lang)}


def _user_display_name(user) -> str:
    if not user or not user.is_authenticated:
        return ''
    # 1. Profile display_name
    try:
        name = (user.profile.display_name or '').strip()
        if name:
            return name
    except Exception:
        pass
    # 2. Full name
    name = (user.get_full_name() or '').strip()
    if name:
        return name
    # 3. Username (email-as-username ise @ öncesini al)
    username = (user.username or '').strip()
    if username:
        return username.split('@')[0] if '@' in username else username
    return 'Kullanıcı'

def _user_info(request) -> dict:
    if request.user.is_authenticated:
        return {
            'display_name': _user_display_name(request.user),
            'email':        request.user.email,
            'user':         request.user,
        }
    return {'display_name': '', 'email': '', 'user': None}


def _is_doctor(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        return user.profile.is_doctor
    except Exception:
        return False


def _get_user_pending_comments(request, article=None, question=None):
    qs = Comment.objects.filter(status='pending', parent__isnull=True)
    if article:
        qs = qs.filter(article=article)
    if question:
        qs = qs.filter(question=question)
    if request.user.is_authenticated:
        return qs.filter(user=request.user).order_by('created_at')
    pending_pks = request.session.get('pending_comment_pks', [])
    if pending_pks:
        return qs.filter(pk__in=pending_pks).order_by('created_at')
    return qs.none()


# ─────────────────────────────────────────────────────────────────────────────
# HOME
# ─────────────────────────────────────────────────────────────────────────────

def home(request):
    ctx  = _base_ctx(request)
    lang = ctx['language']

    articles = Article.objects.filter(
        language=lang, is_published=True
    ).order_by('-view_count', '-published_at')[:8]

    article_count  = Article.objects.filter(language=lang, is_published=True).count()
    question_count = Question.objects.filter(
        status='approved', language=lang
    ).exclude(answer='').exclude(answer__isnull=True).count()

    # Hot questions: article bağlı OLMAYAN, skor algoritması, top 5
    global_qs = (
        Question.objects
        .filter(status='approved', language=lang, article__isnull=True)
        .annotate(comment_count=Count('comments', filter=Q(comments__status='approved')))
        .order_by('-created_at')[:50]
    )
    scored = []
    for q in global_qs:
        score = (q.votes or 0) * 3 + (q.comment_count or 0) * 2 + (5 if q.answer else 0)
        scored.append({'question': q, 'score': score, 'comment_count': q.comment_count})
    scored.sort(key=lambda x: x['score'], reverse=True)

    # Topics: DB'den çek, yoksa fallback template'te
    topics = ArticleTag.objects.filter(
        language__in=[lang, 'both']
    ).order_by('order', 'name')

    # Makale öneri: home'da oturum bazlı (exclude yok çünkü liste sayfası)
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    recommended_articles = RecommendationEngine.recommend_articles(
        session_key=session_key,
        language=lang,
        exclude_pk=None,
        limit=4,
    )

    ctx.update({
        'articles':              articles.prefetch_related('tags'),
        'article_count':         article_count,
        'question_count':        question_count,
        'hot_questions':         scored[:5],
        'user_display_name':     _user_display_name(request.user),
        'topics':                topics,
        'recommended_articles':  recommended_articles,
    })
    return render(request, 'soru_cevap/home.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE PAGE
# ─────────────────────────────────────────────────────────────────────────────

def article_page(request, slug):
    ctx     = _base_ctx(request)
    lang    = ctx['language']
    article = get_object_or_404(Article, slug=slug, is_published=True)

    Article.objects.filter(pk=article.pk).update(view_count=F('view_count') + 1)

    # ── Davranış takibi ──────────────────────────────────────────────────────
    session_key = _ensure_session(request)
    UserBehavior.record_view(session_key=session_key, article=article)

    root_comments    = article.comments.filter(status='approved', parent__isnull=True)
    comment_tree     = build_comment_tree(root_comments)
    all_comments     = article.comments.filter(status='approved')
    pending_comments = _get_user_pending_comments(request, article=article)

    avg_rating_val = root_comments.filter(rating__isnull=False).aggregate(a=Avg('rating'))['a']
    avg_rating     = round(avg_rating_val, 1) if avg_rating_val else None
    rating_count   = root_comments.filter(rating__isnull=False).count()

    sidebar_questions = article.questions.filter(
        status='approved'
    ).annotate(
        has_answer=Case(
            When(answer__isnull=False, then=1),
            default=0, output_field=IntegerField(),
        )
    ).order_by('-has_answer', '-votes', '-created_at')[:15]

    is_liked   = Like.objects.filter(article=article, session_key=session_key).exists()
    like_count = article.likes.count()

    # ── Öneri algoritması ─────────────────────────────────────────────────────
    recommended_articles = RecommendationEngine.recommend_articles(
        session_key=session_key,
        language=lang,
        exclude_pk=article.pk,
        limit=4,
    )

    base_url        = request.build_absolute_uri('/')[:-1]
    article_json_ld = article.get_article_json_ld(request)
    faq_json_ld     = article.get_faq_json_ld()
    review_json_ld  = article.get_review_json_ld(base_url)

    prefix = ctx['qa_prefix']
    ctx.update({
        'article':               article,
        'comment_tree':          comment_tree,
        'comments':              all_comments,
        'pending_comments':      pending_comments,
        'comment_reply_url':     f'{prefix}/yorum/{article.slug}/',
        'ask_question_url':      f'{prefix}/sor/{article.slug}/',
        'article_questions_url': f'{prefix}/makale-sorular/{article.slug}/',
        'sidebar_questions':     sidebar_questions,
        'avg_rating':            avg_rating,
        'rating_count':          rating_count,
        'is_liked':              is_liked,
        'like_count':            like_count,
        'article_json_ld':       article_json_ld,
        'faq_json_ld':           faq_json_ld,
        'review_json_ld':        review_json_ld,
        'og_image_url':          article.get_image_url(),
        'avg_stars_filled':      range(round(avg_rating_val)) if avg_rating_val else range(0),
        'avg_stars_empty':       range(5 - round(avg_rating_val)) if avg_rating_val else range(5),
        'user_display_name':     _user_display_name(request.user),
        'is_doctor':             _is_doctor(request.user),
        'recommended_articles':  recommended_articles,
        # JS time tracker — template'te data-track-id ve data-track-url olarak kullan
        'track_article_id':      article.pk,
        'track_url':             f'{prefix}/sure-takip/',
    })
    return render(request, 'soru_cevap/article.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# ARTICLE QUESTIONS LIST
# ─────────────────────────────────────────────────────────────────────────────

def article_questions_list(request, slug):
    ctx     = _base_ctx(request)
    article = get_object_or_404(Article, slug=slug, is_published=True)

    questions = article.questions.filter(
        status='approved'
    ).annotate(
        has_answer=Case(
            When(answer__isnull=False, then=1),
            default=0, output_field=IntegerField(),
        )
    ).order_by('-has_answer', '-votes', '-created_at')

    answered_count = questions.exclude(answer='').exclude(answer__isnull=True).count()

    questions_with_comments = []
    for q in questions:
        questions_with_comments.append({
            'question':      q,
            'comment_count': q.comments.filter(status='approved').count(),
            'qa_json_ld':    q.get_json_ld(request),
        })

    prefix = ctx['qa_prefix']
    ctx.update({
        'article':                   article,
        'questions':                 questions,
        'questions_with_comments':   questions_with_comments,
        'answered_count':            answered_count,
        'faq_json_ld':               article.get_faq_json_ld(),
        'ask_question_url':          f'{prefix}/sor/{article.slug}/',
        'page_title':                f'{article.title} — Sorular',
        'page_description':          f'{article.title} konusunda sorular ve uzman cevapları.',
        'user_display_name':         _user_display_name(request.user),
        'is_doctor':                 _is_doctor(request.user),
        'answer_question_url_base':  f'{prefix}/soru-cevapla/',
    })
    return render(request, 'soru_cevap/article_questions.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTIONS LIST
# ─────────────────────────────────────────────────────────────────────────────

def questions_list(request):
    ctx  = _base_ctx(request)
    lang = ctx['language']

    # Temel queryset — article bağlı olmayan onaylı sorular
    base_qs = Question.objects.filter(
        status='approved', language=lang, article__isnull=True
    ).annotate(
        has_answer=Case(
            When(answer__isnull=False, then=1),
            default=0, output_field=IntegerField(),
        ),
        comment_count=Count('comments', filter=Q(comments__status='approved')),
    )

    # ── Filtre parametresi ───────────────────────────────────────────────────
    filter_param = request.GET.get('filter', 'all')

    if filter_param == 'answered':
        questions = base_qs.exclude(
            answer='').exclude(answer__isnull=True
        ).order_by('-answered_at', '-created_at')

    elif filter_param == 'pending':
        questions = base_qs.filter(
            Q(answer='') | Q(answer__isnull=True)
        ).order_by('-created_at')

    elif filter_param == 'hot':
        # Önce çek, sonra Python'da skorla
        qs_list = list(base_qs.order_by('-created_at')[:200])
        
        def hot_score(q):
            rating = q.get_avg_rating() or 0
            answer_bonus = 10 if q.answer else 0
            return (
                (q.votes or 0) * 3 +
                (q.comment_count or 0) * 2 +
                rating * 4 +
                answer_bonus
            )
        
        questions = sorted(qs_list, key=hot_score, reverse=True)
    else:  # 'all'
        questions = base_qs.order_by('-created_at')

    answered_count = base_qs.exclude(answer='').exclude(answer__isnull=True).count()

    questions_with_comments = []
    for q in questions:
        questions_with_comments.append({
            'question':      q,
            'comment_count': getattr(q, 'comment_count', 0),
            'qa_json_ld':    q.get_json_ld(request),
        })


    ctx.update({
        'questions':               questions,
        'questions_with_comments': questions_with_comments,
        'answered_count':          answered_count,
        'active_filter':           filter_param,   # ← template filtre butonları için
        'page_title': (
            'Diş Hekimine Soru Sor — Tüm Sorular | Dr. Devrim Dental Forum'
            if lang == 'tr' else
            'Ask a Dentist — All Questions | Dr. Devrim Dental Forum'
        ),
        'page_description': (
            'Hastalardan gelen diş sağlığı soruları ve uzman diş hekimi cevapları.'
            if lang == 'tr' else
            'Patient dental questions with expert dentist answers.'
        ),
        'is_doctor':                _is_doctor(request.user),
        'answer_question_url_base': f'{_qa_prefix(lang)}/soru-cevapla/',
        'display_name':             _user_display_name(request.user),
        'user_display_name':        _user_display_name(request.user),
    })
    return render(request, 'soru_cevap/questions.html', ctx)

# ─────────────────────────────────────────────────────────────────────────────
# ARTICLES LIST  — tag filtreli makale listesi
# /soru-cevap/makaleler/?tag=implant
# ─────────────────────────────────────────────────────────────────────────────

def articles_list(request):
    ctx  = _base_ctx(request)
    lang = ctx['language']

    tag_slug    = request.GET.get('tag', '').strip()
    active_tag  = None

    articles_qs = Article.objects.filter(
        language=lang, is_published=True
    ).prefetch_related('tags').order_by('-view_count', '-published_at')

    if tag_slug:
        try:
            active_tag = ArticleTag.objects.get(slug=tag_slug.lower())
            articles_qs = articles_qs.filter(tags=active_tag)
        except ArticleTag.DoesNotExist:
            active_tag = None

    # Sidebar tag listesi — tüm aktif tag'ler (makale sayısıyla)
    all_tags = (
        ArticleTag.objects
        .filter(language__in=[lang, 'both'])
        .annotate(article_count=DjCount(
            'articles',
            filter=Q(articles__is_published=True, articles__language=lang)
        ))
        .order_by('order', 'name')
    )


    total_count = articles_qs.count()

    ctx.update({
        'articles':       articles_qs,
        'active_tag':     active_tag,
        'all_tags':       all_tags,
        'total_count':    total_count,
        'tag_slug':       tag_slug,
        'display_name': _user_display_name(request.user),
    })
    return render(request, 'soru_cevap/articles_list.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# QUESTION DETAIL
# ─────────────────────────────────────────────────────────────────────────────

def question_detail(request, question_id, slug=None):
    ctx      = _base_ctx(request)
    question = get_object_or_404(Question, pk=question_id, status='approved')

    if slug and slug != question.slug:
        return redirect(question.get_absolute_url(), permanent=True)

    root_comments    = question.comments.filter(status='approved', parent__isnull=True)
    comment_tree     = build_comment_tree(root_comments)
    all_comments     = question.comments.filter(status='approved')
    pending_comments = _get_user_pending_comments(request, question=question)
    json_ld          = question.get_json_ld(request)

    session_key  = _ensure_session(request)
    is_liked     = QuestionLike.objects.filter(question=question, session_key=session_key).exists()
    like_count   = question.question_likes.count()
    avg_rating   = question.get_avg_rating()
    rating_count = question.get_rating_count()

    related_questions = []
    if question.article:
        related_questions = list(
            question.article.questions.filter(
                status='approved'
            ).exclude(pk=question.pk).order_by('-votes', '-created_at')[:5]
        )

    prefix = ctx['qa_prefix']
    ctx.update({
        'question':            question,
        'comment_tree':        comment_tree,
        'comments':            all_comments,
        'pending_comments':    pending_comments,
        'comment_reply_url':   f'{prefix}/soru-yorum/{question.pk}/',
        'answer_question_url': f'{prefix}/soru-cevapla/{question.pk}/',
        'like_question_url':   f'{prefix}/soru-begen/{question.pk}/',
        'json_ld':             json_ld,
        'page_title':          question.display_title,
        'page_description': (
            (question.answer[:155] + '…') if question.answer else question.text[:155]
        ),
        'is_liked':            is_liked,
        'like_count':          like_count,
        'avg_rating':          avg_rating,
        'rating_count':        rating_count,
        'avg_stars_filled':    range(round(avg_rating)) if avg_rating else range(0),
        'avg_stars_empty':     range(5 - round(avg_rating)) if avg_rating else range(5),
        'related_questions':   related_questions,
        'user_display_name':   _user_display_name(request.user),
        'is_doctor':           _is_doctor(request.user),
        'display_name': _user_display_name(request.user),
    })
    return render(request, 'soru_cevap/question_detail.html', ctx)


# ─────────────────────────────────────────────────────────────────────────────
# POST: COMMENT ARTICLE
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def comment_article(request, slug):
    article   = get_object_or_404(Article, slug=slug, is_published=True)
    text      = request.POST.get('text', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    if not text:
        return redirect(article.get_absolute_url() + '#yorumlar')

    info   = _user_info(request)
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(pk=int(parent_id), status='approved')
        except (Comment.DoesNotExist, ValueError):
            pass

    rating = None
    if parent is None:
        rating_raw = request.POST.get('rating', '')
        if rating_raw and rating_raw.isdigit():
            r = int(rating_raw)
            if 1 <= r <= 5:
                rating = r

    # ── AI Moderasyon ────────────────────────────────────────────────────────
    ai_status = auto_moderate(text, content_type='comment')

    # Her durumda kaydet — rejected bile olsa adminде görünsün
    Comment.objects.create(
        article=article, parent=parent, text=text, rating=rating,
        display_name=info['display_name'], email=info['email'], user=info['user'],
        status=ai_status,  # 'approved' | 'pending' | 'rejected'
    )

    session_key = _ensure_session(request)
    UserBehavior.record_comment(
        session_key=session_key,
        article=article,
        rating=float(rating) if rating else None,
    )

    if ai_status == 'rejected':
        anchor = '#yorumlar?rejected=1'
    elif ai_status == 'approved':
        anchor = '#yorumlar'
    else:
        anchor = '#yorumlar?pending=1'

    return redirect(article.get_absolute_url() + anchor)


# ─────────────────────────────────────────────────────────────────────────────
# POST: LIKE ARTICLE
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def like_article(request, slug):
    article     = get_object_or_404(Article, slug=slug, is_published=True)
    session_key = _ensure_session(request)

    obj, created = Like.objects.get_or_create(article=article, session_key=session_key)
    if not created:
        obj.delete()
        liked = False
    else:
        liked = True

    UserBehavior.record_like(session_key=session_key, article=article, liked=liked)
    like_count = article.likes.count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'count': like_count})
    return redirect(article.get_absolute_url())


# ─────────────────────────────────────────────────────────────────────────────
# POST: ASK QUESTION (article bağlı)
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def ask_question(request, slug):
    article = get_object_or_404(Article, slug=slug, is_published=True)
    text    = request.POST.get('text', '').strip()
    title   = request.POST.get('title', '').strip()

    if not text:
        return redirect(article.get_absolute_url() + '#soru-sor')

    info = _user_info(request)

    image_url = ''
    uploaded = request.FILES.get('image')
    if uploaded:
        allowed = {'image/jpeg', 'image/png', 'image/webp'}
        if uploaded.content_type in allowed and uploaded.size <= 5 * 1024 * 1024:
            import base64
            b64 = base64.b64encode(uploaded.read()).decode('utf-8')
            image_url = f'data:{uploaded.content_type};base64,{b64}'

    # ── AI Moderasyon ────────────────────────────────────────────────────────
    moderation_text = f"{title}\n\n{text}".strip() if title else text
    ai_status = auto_moderate(moderation_text, content_type='question')


    # Her durumda kaydet
    Question.objects.create(
        article=article, language=article.language, title=title, text=text,
        display_name=info['display_name'], email=info['email'], user=info['user'],
        image=image_url,
        status=ai_status,  # 'approved' | 'pending' | 'rejected'
    )

    session_key = _ensure_session(request)
    UserBehavior.record_question(session_key=session_key, article=article)

    if ai_status == 'rejected':
        anchor = '#soru-sor?rejected=1'
    elif ai_status == 'approved':
        anchor = '#soru-sor'
    else:
        anchor = '#soru-sor?pending=1'

    return redirect(article.get_absolute_url() + anchor)


# ─────────────────────────────────────────────────────────────────────────────
# POST: COMMENT QUESTION
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def comment_question(request, question_id):
    question  = get_object_or_404(Question, pk=question_id, status='approved')
    text      = request.POST.get('text', '').strip()
    parent_id = request.POST.get('parent_id', '').strip()

    if not text:
        return redirect(question.get_absolute_url() + '#yorumlar')

    info   = _user_info(request)
    parent = None
    if parent_id:
        try:
            parent = Comment.objects.get(pk=int(parent_id), status='approved')
        except (Comment.DoesNotExist, ValueError):
            pass

    rating = None
    if parent is None:
        rating_raw = request.POST.get('rating', '')
        if rating_raw and rating_raw.isdigit():
            r = int(rating_raw)
            if 1 <= r <= 5:
                rating = r

    # ── AI Moderasyon ────────────────────────────────────────────────────────
    ai_status = auto_moderate(text, content_type='comment')

    # Her durumda kaydet
    Comment.objects.create(
        question=question, parent=parent, text=text, rating=rating,
        display_name=info['display_name'], email=info['email'], user=info['user'],
        status=ai_status,  # 'approved' | 'pending' | 'rejected'
    )

    if ai_status == 'rejected':
        anchor = '#yorumlar?rejected=1'
    elif ai_status == 'approved':
        anchor = '#yorumlar'
    else:
        anchor = '#yorumlar?pending=1'

    return redirect(question.get_absolute_url() + anchor)


# ─────────────────────────────────────────────────────────────────────────────
# POST: ANSWER QUESTION
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def answer_question(request, question_id):
    if not _is_doctor(request.user):
        return redirect('/')

    question = get_object_or_404(Question, pk=question_id, status='approved')
    answer   = request.POST.get('answer', '').strip()

    if answer:
        from django.utils import timezone
        question.answer      = answer
        question.answered_by = request.user
        question.answered_at = timezone.now()
        question.save()

    next_url = request.POST.get('next', '') or question.get_absolute_url()
    return redirect(next_url)


# ─────────────────────────────────────────────────────────────────────────────
# POST: GLOBAL QUESTION (sorular listesi sayfasından)
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
@login_required
def ask_global_question(request):
    ctx   = _base_ctx(request)
    text  = request.POST.get('text', '').strip()
    title = request.POST.get('title', '').strip()

    if not text:
        return redirect(ctx['qa_prefix'] + '/sorular/')

    info = _user_info(request)

    image_url = ''
    uploaded = request.FILES.get('image')
    if uploaded:
        allowed = {'image/jpeg', 'image/png', 'image/webp'}
        if uploaded.content_type in allowed and uploaded.size <= 5 * 1024 * 1024:
            import base64
            b64 = base64.b64encode(uploaded.read()).decode('utf-8')
            image_url = f'data:{uploaded.content_type};base64,{b64}'

    # ── AI Moderasyon ────────────────────────────────────────────────────────
    moderation_text = f"{title}\n\n{text}".strip() if title else text
    ai_status = auto_moderate(moderation_text, content_type='question')


    # Her durumda kaydet
    Question.objects.create(
        language=ctx['language'], title=title, text=text,
        display_name=info['display_name'], email=info['email'], user=info['user'],
        image=image_url,
        status=ai_status,  # 'approved' | 'pending' | 'rejected'
    )

    if ai_status == 'rejected':
        param = 'rejected=1'
    elif ai_status == 'approved':
        param = 'asked=1'
    else:
        param = 'asked=1&pending=1'

    source = request.POST.get('source', 'questions')
    if source == 'home':
        return redirect(f"{ctx['qa_prefix']}/?{param}")
    else:
        return redirect(f"{ctx['qa_prefix']}/sorular/?{param}")

# ─────────────────────────────────────────────────────────────────────────────
# POST: LIKE QUESTION
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def like_question(request, question_id):
    question    = get_object_or_404(Question, pk=question_id, status='approved')
    session_key = _ensure_session(request)

    obj, created = QuestionLike.objects.get_or_create(question=question, session_key=session_key)
    if not created:
        obj.delete()
        liked = False
    else:
        liked = True

    like_count = question.question_likes.count()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'count': like_count})
    return redirect(question.get_absolute_url())


# ─────────────────────────────────────────────────────────────────────────────
# POST: SURE TAKIP — JS Time Tracker endpoint
# ─────────────────────────────────────────────────────────────────────────────

@require_POST
def sure_takip(request):
    """
    article.html JS tarafından çağrılır.
    JSON body: { "article_id": <int>, "seconds": <int> }

    Template'te kullanım (data attribute, {{ }} tag JS içine YAZILMAZ):
        <div id="time-tracker"
             data-article-id="{{ track_article_id }}"
             data-track-url="{{ track_url }}">
        </div>

    JS:
        var el = document.getElementById('time-tracker');
        var articleId = el.dataset.articleId;
        var trackUrl  = el.dataset.trackUrl;
    """
    try:
        data       = json_lib.loads(request.body)
        article_id = int(data.get('article_id', 0))
        seconds    = int(data.get('seconds', 0))
    except (ValueError, TypeError, json_lib.JSONDecodeError):
        return JsonResponse({'ok': False, 'error': 'invalid payload'}, status=400)

    if article_id <= 0 or seconds <= 0:
        return JsonResponse({'ok': False, 'error': 'invalid values'}, status=400)

    try:
        article = Article.objects.get(pk=article_id, is_published=True)
    except Article.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)

    session_key = _ensure_session(request)
    UserBehavior.record_time(session_key=session_key, article=article, seconds=seconds)
    return JsonResponse({'ok': True})