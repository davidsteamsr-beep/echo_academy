from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from bot.config import ADMIN_ID, DATABASE_URL, GROUP_SEAT, GROUP_SIZE, INDIVIDUAL_PRICE, ROOT


class Base(DeclarativeBase):
    pass


class Role(str, enum.Enum):
    admin = "admin"
    traffer = "traffer"
    teacher = "teacher"
    student = "student"


class CourseType(str, enum.Enum):
    individual = "individual"
    group = "group"


class LeadStatus(str, enum.Enum):
    new = "new"
    calling = "calling"
    rejected = "rejected"
    waiting_payment = "waiting_payment"
    paid = "paid"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class PayoutStatus(str, enum.Enum):
    unpaid = "unpaid"
    paid = "paid"


def _enum(kind: type[enum.Enum], name: str) -> Enum:
    return Enum(kind, name=name, native_enum=False, length=32, values_callable=lambda items: [i.value for i in items])


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), default=Role.student)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ref_code: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    type: Mapped[CourseType] = mapped_column(_enum(CourseType, "course_type"))
    base_price: Mapped[float] = mapped_column(Float)
    duration_days: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    traffer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"))
    status: Mapped[LeadStatus] = mapped_column(_enum(LeadStatus, "lead_status"), default=LeadStatus.new)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Deal(Base):
    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lead_id: Mapped[int] = mapped_column(Integer, ForeignKey("leads.id"))
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    traffer_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    total_amount: Mapped[float] = mapped_column(Float)
    traffer_cut: Mapped[float] = mapped_column(Float, default=0.0)
    teacher_cut: Mapped[float] = mapped_column(Float, default=0.0)
    admin_cut: Mapped[float] = mapped_column(Float, default=0.0)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        _enum(PaymentStatus, "payment_status"), default=PaymentStatus.pending
    )
    payout_status: Mapped[PayoutStatus] = mapped_column(
        _enum(PayoutStatus, "payout_status"), default=PayoutStatus.unpaid
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


def _make_engine():
    if DATABASE_URL:
        return create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    # Local dev fallback
    sqlite_path = ROOT / "echo.sqlite"
    return create_async_engine(f"sqlite+aiosqlite:///{sqlite_path}")


engine = _make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@dataclass
class Notice:
    user_id: int
    text: str


@dataclass
class OpResult:
    ok: bool
    text: str
    notices: list[Notice] = field(default_factory=list)


def rub(amount: float) -> str:
    return f"{int(round(amount)):,}".replace(",", " ") + " ₽"


def split_individual(has_traffer: bool) -> tuple[float, float, float, float]:
    total = INDIVIDUAL_PRICE
    traffer = total * 0.10 if has_traffer else 0.0
    teacher = total * 0.50
    admin = total - traffer - teacher
    return total, traffer, teacher, admin


def split_group_seat(has_traffer: bool) -> tuple[float, float, float, float]:
    total = GROUP_SEAT
    traffer = total * 0.15 if has_traffer else 0.0
    teacher = total * 0.50
    admin = total - traffer - teacher
    return total, traffer, teacher, admin


def split_group_bundle(has_traffer: bool) -> tuple[float, float, float, float]:
    total = GROUP_SEAT * GROUP_SIZE
    traffer = GROUP_SEAT * 0.15 * GROUP_SIZE if has_traffer else 0.0
    teacher = total * 0.50
    admin = total - traffer - teacher
    return total, traffer, teacher, admin


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Course))
        if not count:
            session.add_all(
                [
                    Course(title="Моушн-дизайн", type=CourseType.individual, base_price=INDIVIDUAL_PRICE, duration_days=60),
                    Course(title="Разработка ботов", type=CourseType.group, base_price=GROUP_SEAT, duration_days=45),
                    Course(title="Саунд-дизайн", type=CourseType.individual, base_price=INDIVIDUAL_PRICE, duration_days=50),
                ]
            )
            await session.commit()


async def get_user(user_id: int) -> User | None:
    async with SessionLocal() as session:
        return await session.get(User, user_id)


async def get_user_by_ref(code: str) -> User | None:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.ref_code == code))
        return result.scalar_one_or_none()


async def touch_user(user_id: int, username: str | None, full_name: str) -> tuple[User, bool]:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        created = False
        if user is None:
            role = Role.admin if ADMIN_ID and user_id == ADMIN_ID else Role.student
            user = User(
                id=user_id,
                username=username,
                full_name=full_name or "Без имени",
                role=role,
                balance=0.0,
                is_active=True,
                ref_code=f"user_{user_id}",
            )
            session.add(user)
            created = True
        else:
            user.username = username
            user.full_name = full_name or user.full_name
            if ADMIN_ID and user_id == ADMIN_ID:
                user.role = Role.admin
        await session.commit()
        await session.refresh(user)
        return user, created


async def set_role(user_id: int, role: Role) -> User | None:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            return None
        user.role = role
        await session.commit()
        await session.refresh(user)
        return user


async def list_courses() -> list[Course]:
    async with SessionLocal() as session:
        result = await session.execute(select(Course).order_by(Course.id))
        return list(result.scalars().all())


async def first_course() -> Course | None:
    courses = await list_courses()
    return courses[0] if courses else None


async def create_referral_lead(student_id: int, traffer_id: int) -> Lead | None:
    async with SessionLocal() as session:
        course = await session.scalar(select(Course).order_by(Course.id).limit(1))
        if course is None:
            return None
        existing = await session.scalar(
            select(Lead).where(
                Lead.student_id == student_id,
                Lead.status.in_([LeadStatus.new, LeadStatus.calling, LeadStatus.waiting_payment]),
            )
        )
        if existing:
            return existing
        lead = Lead(
            student_id=student_id,
            traffer_id=traffer_id,
            course_id=course.id,
            status=LeadStatus.new,
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        return lead


async def list_lead_rows() -> list[tuple[Lead, str, str, int | None]]:
    async with SessionLocal() as session:
        result = await session.execute(select(Lead).order_by(Lead.id.desc()))
        leads = list(result.scalars().all())
        rows: list[tuple[Lead, str, str, int | None]] = []
        for lead in leads:
            student = await session.get(User, lead.student_id)
            course = await session.get(Course, lead.course_id)
            rows.append(
                (
                    lead,
                    student.full_name if student else "—",
                    course.title if course else "—",
                    lead.traffer_id,
                )
            )
        return rows


async def traffer_stats(traffer_id: int) -> tuple[int, int]:
    async with SessionLocal() as session:
        leads = list(
            (await session.execute(select(Lead).where(Lead.traffer_id == traffer_id))).scalars().all()
        )
        paid = sum(1 for lead in leads if lead.status == LeadStatus.paid)
        return paid, len(leads)


async def deals_for_student(student_id: int) -> list[tuple[Deal, str]]:
    return await _deals(Deal.student_id == student_id)


async def deals_for_teacher(teacher_id: int) -> list[tuple[Deal, str]]:
    return await _deals(Deal.teacher_id == teacher_id)


async def _deals(criterion) -> list[tuple[Deal, str]]:
    async with SessionLocal() as session:
        result = await session.execute(select(Deal).where(criterion).order_by(Deal.id.desc()))
        deals = list(result.scalars().all())
        rows: list[tuple[Deal, str]] = []
        for deal in deals:
            lead = await session.get(Lead, deal.lead_id)
            course = await session.get(Course, lead.course_id) if lead else None
            student = await session.get(User, deal.student_id)
            title = course.title if course else "Курс"
            if student:
                title = f"{student.full_name} · {title}"
            rows.append((deal, title))
        return rows


async def open_leads(student_id: int) -> list[tuple[Lead, Course]]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Lead).where(
                Lead.student_id == student_id,
                Lead.status.in_([LeadStatus.new, LeadStatus.calling, LeadStatus.waiting_payment]),
            )
        )
        rows: list[tuple[Lead, Course]] = []
        for lead in result.scalars().all():
            course = await session.get(Course, lead.course_id)
            if course:
                rows.append((lead, course))
        return rows


async def open_invoice(student_id: int, course_id: int) -> OpResult:
    async with SessionLocal() as session:
        course = await session.get(Course, course_id)
        if course is None:
            return OpResult(False, "Курс не найден.")
        existing = await session.scalar(
            select(Lead).where(
                Lead.student_id == student_id,
                Lead.course_id == course_id,
                Lead.status.in_([LeadStatus.new, LeadStatus.calling, LeadStatus.waiting_payment]),
            )
        )
        if existing:
            return OpResult(True, f"Счёт по «{course.title}» уже открыт. Нажмите «Оплатить».")
        lead = Lead(
            student_id=student_id,
            traffer_id=None,
            course_id=course_id,
            status=LeadStatus.waiting_payment,
        )
        session.add(lead)
        await session.commit()
        return OpResult(True, f"Счёт на «{course.title}» — {rub(course.base_price)}. Нажмите «Оплатить».")


async def users_with_balance() -> list[User]:
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.balance > 0).order_by(User.balance.desc()))
        return list(result.scalars().all())


async def admin_ids() -> list[int]:
    async with SessionLocal() as session:
        result = await session.execute(select(User.id).where(User.role == Role.admin))
        ids = {int(row) for row in result.scalars().all()}
    if ADMIN_ID:
        ids.add(ADMIN_ID)
    return sorted(ids)


async def system_stats() -> str:
    async with SessionLocal() as session:
        users = list((await session.execute(select(User))).scalars().all())
        leads = list((await session.execute(select(Lead))).scalars().all())
        deals = list((await session.execute(select(Deal))).scalars().all())
    by_role = {role: sum(1 for user in users if user.role == role) for role in Role}
    paid = sum(1 for lead in leads if lead.status == LeadStatus.paid)
    total_leads = len(leads)
    rate = round(100 * paid / total_leads) if total_leads else 0
    turnover = sum(deal.total_amount for deal in deals)
    owed = sum(user.balance for user in users)
    return (
        "Статистика системы\n"
        f"Люди: админы {by_role[Role.admin]}, траферы {by_role[Role.traffer]}, "
        f"преподаватели {by_role[Role.teacher]}, ученики {by_role[Role.student]}\n"
        f"Лиды: {total_leads}, оплачено {paid}, конверсия {rate}%\n"
        f"Оборот сделок: {rub(turnover)}\n"
        f"К выплате на балансах: {rub(owed)}"
    )


def _credit(session_user: User | None, amount: float) -> None:
    if session_user is None or amount <= 0:
        return
    session_user.balance = round((session_user.balance or 0) + amount, 2)


async def _apply(
    session: AsyncSession,
    *,
    student: User,
    teacher: User,
    traffer: User | None,
    course: Course,
    total: float,
    traffer_cut: float,
    teacher_cut: float,
    admin_cut: float,
    lead: Lead | None,
    group_id: str | None,
) -> tuple[Deal, list[Notice]]:
    if lead is None:
        lead = Lead(
            student_id=student.id,
            traffer_id=traffer.id if traffer else None,
            course_id=course.id,
            status=LeadStatus.paid,
        )
        session.add(lead)
        await session.flush()
    else:
        lead.status = LeadStatus.paid
        lead.course_id = course.id
        lead.traffer_id = traffer.id if traffer else lead.traffer_id
    deal = Deal(
        lead_id=lead.id,
        student_id=student.id,
        traffer_id=traffer.id if traffer else None,
        teacher_id=teacher.id,
        group_id=group_id,
        total_amount=total,
        traffer_cut=traffer_cut,
        teacher_cut=teacher_cut,
        admin_cut=admin_cut,
        payment_status=PaymentStatus.success,
        payout_status=PayoutStatus.unpaid,
    )
    session.add(deal)
    if traffer and traffer_cut:
        _credit(traffer, traffer_cut)
    _credit(teacher, teacher_cut)
    admin = await session.scalar(select(User).where(User.role == Role.admin).limit(1))
    if admin is None and ADMIN_ID:
        admin = await session.get(User, ADMIN_ID)
    _credit(admin, admin_cut)
    await session.flush()
    notices: list[Notice] = []
    if traffer and traffer_cut:
        notices.append(Notice(traffer.id, f"Начисление {rub(traffer_cut)} · {student.full_name} · {course.title}"))
    notices.append(Notice(teacher.id, f"Начисление {rub(teacher_cut)} · {student.full_name} · {course.title}"))
    if admin:
        notices.append(Notice(admin.id, f"Сделка #{deal.id} · {student.full_name} · {rub(total)}. Вам {rub(admin_cut)}"))
    notices.append(Notice(student.id, f"Оплата принята: {course.title} · {rub(total)}"))
    return deal, notices


async def mock_payment(lead_id: int) -> OpResult:
    async with SessionLocal() as session:
        lead = await session.get(Lead, lead_id)
        if lead is None:
            return OpResult(False, "Заявка не найдена.")
        if lead.status == LeadStatus.paid:
            return OpResult(False, "Заявка уже оплачена.")
        if lead.status == LeadStatus.rejected:
            return OpResult(False, "По заявке отказ.")
        course = await session.get(Course, lead.course_id)
        student = await session.get(User, lead.student_id)
        if course is None or student is None:
            return OpResult(False, "Курс или ученик потерялись.")
        teacher = await session.scalar(select(User).where(User.role == Role.teacher, User.is_active.is_(True)).limit(1))
        if teacher is None:
            return OpResult(False, "Нет преподавателя. Назначьте роль командой /role.")
        traffer = await session.get(User, lead.traffer_id) if lead.traffer_id else None
        has_traffer = traffer is not None
        if course.type == CourseType.group:
            total, traffer_cut, teacher_cut, admin_cut = split_group_seat(has_traffer)
            group_id = f"seat-{lead.id}"
        else:
            total, traffer_cut, teacher_cut, admin_cut = split_individual(has_traffer)
            group_id = None
        deal, notices = await _apply(
            session,
            student=student,
            teacher=teacher,
            traffer=traffer,
            course=course,
            total=total,
            traffer_cut=traffer_cut,
            teacher_cut=teacher_cut,
            admin_cut=admin_cut,
            lead=lead,
            group_id=group_id,
        )
        await session.commit()
        return OpResult(True, f"Оплата прошла. Сделка #{deal.id} на {rub(total)}.", notices)


async def open_deal(student_id: int, teacher_id: int, traffer_id: int | None, course_type: str) -> OpResult:
    async with SessionLocal() as session:
        student = await session.get(User, student_id)
        teacher = await session.get(User, teacher_id)
        traffer = await session.get(User, traffer_id) if traffer_id else None
        if student is None:
            return OpResult(False, "Ученик не найден.")
        if student.role != Role.student:
            return OpResult(False, "Этот ID не ученик.")
        if teacher is None or teacher.role != Role.teacher:
            return OpResult(False, "Преподаватель не найден.")
        if traffer_id and (traffer is None or traffer.role != Role.traffer):
            return OpResult(False, "Трафер не найден.")
        kind = CourseType.group if course_type == "group" else CourseType.individual
        course = await session.scalar(select(Course).where(Course.type == kind).order_by(Course.id).limit(1))
        if course is None:
            return OpResult(False, "Курс этого типа не заведён.")
        if kind == CourseType.group:
            total, traffer_cut, teacher_cut, admin_cut = split_group_bundle(traffer is not None)
        else:
            total, traffer_cut, teacher_cut, admin_cut = split_individual(traffer is not None)
        lead = await session.scalar(
            select(Lead)
            .where(
                Lead.student_id == student.id,
                Lead.status.in_([LeadStatus.new, LeadStatus.calling, LeadStatus.waiting_payment]),
            )
            .order_by(Lead.id.desc())
            .limit(1)
        )
        deal, notices = await _apply(
            session,
            student=student,
            teacher=teacher,
            traffer=traffer,
            course=course,
            total=total,
            traffer_cut=traffer_cut,
            teacher_cut=teacher_cut,
            admin_cut=admin_cut,
            lead=lead,
            group_id=None,
        )
        if kind == CourseType.group:
            deal.group_id = f"G-{deal.id}"
        await session.commit()
        text = (
            f"Сделка #{deal.id}\n"
            f"{student.full_name} · {course.title}\n"
            f"Сумма {rub(total)}\n"
            f"Трафер {rub(traffer_cut)}\n"
            f"Преподаватель {rub(teacher_cut)}\n"
            f"Админ {rub(admin_cut)}"
        )
        return OpResult(True, text, notices)


async def payout(user_id: int, amount: float) -> OpResult:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        if user is None:
            return OpResult(False, "Пользователь не найден.")
        if amount <= 0:
            return OpResult(False, "Сумма должна быть больше нуля.")
        if amount - (user.balance or 0) > 0.01:
            return OpResult(False, f"На балансе только {rub(user.balance or 0)}.")
        user.balance = round((user.balance or 0) - amount, 2)
        cleared = user.balance <= 0.01
        if cleared:
            user.balance = 0
            result = await session.execute(
                select(Deal).where(
                    Deal.payout_status == PayoutStatus.unpaid,
                    (Deal.traffer_id == user_id) | (Deal.teacher_id == user_id),
                )
            )
            for deal in result.scalars().all():
                deal.payout_status = PayoutStatus.paid
        await session.commit()
        return OpResult(
            True,
            f"Выплачено {rub(amount)}. Остаток {rub(user.balance)}.",
            [Notice(user.id, f"Выплата {rub(amount)}. Остаток {rub(user.balance)}.")],
        )
