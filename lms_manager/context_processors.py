"""
Context processor tự động build breadcrumb cho các trang lms_manager
dựa trên URL pattern và resolver_match.
"""


def breadcrumb(request):
    items = []
    if not request.resolver_match:
        return {"breadcrumb_items": items}

    url_name = request.resolver_match.url_name or ""
    kwargs = request.resolver_match.kwargs or {}

    # Định nghĩa map: url_name -> (label, parent_url_name)
    mapping = {
        "classroom_list": ("Lớp học", None),
        "classroom_add": ("Lớp học", "classroom_list"),
        "classroom_detail": ("Lớp học", "classroom_list"),
        "classroom_edit": ("Lớp học", "classroom_list"),

        "subject_list": ("Môn học", None),
        "subject_add": ("Môn học", "subject_list"),
        "subject_edit": ("Môn học", "subject_list"),

        "teacher_list": ("Giảng viên", None),
        "teacher_add": ("Giảng viên", "teacher_list"),
        "teacher_detail": ("Giảng viên", "teacher_list"),
        "teacher_edit": ("Giảng viên", "teacher_list"),
        "teacher_import_excel": ("Giảng viên", "teacher_list"),

        "student_list": ("Học sinh", None),
        "student_add": ("Học sinh", "student_list"),
        "student_detail": ("Học sinh", "student_list"),
        "student_edit": ("Học sinh", "student_list"),
        "student_register": ("Học sinh", "student_list"),

        "payment_period_list": ("Đợt đóng tiền", None),
        "payment_period_add": ("Đợt đóng tiền", "payment_period_list"),
        "payment_period_edit": ("Đợt đóng tiền", "payment_period_list"),

        "payment_list": ("Giao dịch đóng tiền", None),
        "payment_add": ("Giao dịch đóng tiền", "payment_list"),
        "payment_receipt": ("Giao dịch đóng tiền", "payment_list"),

        "debt_dashboard": ("Công nợ học phí", None),
    }

    if url_name not in mapping:
        return {"breadcrumb_items": items}

    label, parent = mapping[url_name]

    # Lấy URL của parent (dựa vào tên)
    from django.urls import reverse, NoReverseMatch
    if parent:
        try:
            items.append({"label": label, "url": reverse(parent)})
        except NoReverseMatch:
            items.append({"label": label})
    else:
        items.append({"label": label})

    # Item hiện tại: dùng label phù hợp theo hành động
    action_labels = {
        "_add": "Thêm mới",
        "_edit": "Chỉnh sửa",
        "_delete": "Xóa",
        "_detail": "Chi tiết",
        "_register": "Đăng ký môn học",
        "_receipt": "In biên lai",
        "_import_excel": "Nhập từ Excel",
    }

    action = ""
    for suffix, txt in action_labels.items():
        if url_name.endswith(suffix):
            action = txt
            break

    if action:
        # Nếu là detail, lấy tên đối tượng nếu có trong context
        if url_name == "classroom_detail":
            obj = kwargs.get("pk")
            items.append({"label": action})
        elif url_name == "student_detail":
            items.append({"label": action})
        elif url_name == "teacher_detail":
            items.append({"label": action})
        else:
            items.append({"label": action})

    return {"breadcrumb_items": items}
