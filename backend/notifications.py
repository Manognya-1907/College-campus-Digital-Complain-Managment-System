def notify_department_on_ticket_create(department: str, title: str, ticket_id: int):
    print(
        f"[NOTIFY][DEPARTMENT:{department}] New ticket #{ticket_id}: {title}"
    )


def notify_student_on_reply(student_email: str, ticket_id: int):
    print(
        f"[NOTIFY][STUDENT:{student_email}] New reply added on ticket #{ticket_id}"
    )
