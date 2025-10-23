# 이 내용을 core/views.py 파일 끝에 추가하세요

@login_required
def declaration_add_view(request, service_slug):
    """신고서 추가 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)

    if request.method == 'POST':
        form = DeclarationForm(request.POST)
        if form.is_valid():
            declaration = form.save(commit=False)
            declaration.service = service
            declaration.save()
            messages.success(request, f'{declaration.name} 신고서가 추가되었습니다.')
            return redirect('service_detail', service_slug=service.slug)
    else:
        form = DeclarationForm()

    return render(request, 'core/declaration_form.html', {
        'form': form,
        'service': service,
        'is_edit': False
    })


@login_required
def declaration_edit_view(request, service_slug, declaration_id):
    """신고서 수정 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)
    declaration = get_object_or_404(Declaration, pk=declaration_id, service=service)

    if request.method == 'POST':
        form = DeclarationForm(request.POST, instance=declaration)
        if form.is_valid():
            form.save()
            messages.success(request, f'{declaration.name} 신고서가 수정되었습니다.')
            return redirect('service_detail', service_slug=service.slug)
    else:
        form = DeclarationForm(instance=declaration)

    return render(request, 'core/declaration_form.html', {
        'form': form,
        'service': service,
        'declaration': declaration,
        'is_edit': True
    })


@login_required
@require_http_methods(["POST"])
def declaration_delete_view(request, service_slug, declaration_id):
    """신고서 삭제 (관리자 전용)"""
    if request.user.user_type != 'admin':
        messages.error(request, '관리자만 접근할 수 있습니다.')
        return redirect('dashboard')

    service = get_object_or_404(Service, slug=service_slug)
    declaration = get_object_or_404(Declaration, pk=declaration_id, service=service)

    declaration_name = declaration.name
    declaration.delete()
    messages.success(request, f'{declaration_name} 신고서가 삭제되었습니다.')
    return redirect('service_detail', service_slug=service.slug)
