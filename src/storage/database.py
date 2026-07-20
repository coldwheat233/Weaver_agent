"""SQLAlchemy async engine + session factory + 迁移"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.utils.config import get_settings

settings = get_settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.chroma_dir.mkdir(parents=True, exist_ok=True)
settings.assets_dir.mkdir(parents=True, exist_ok=True)
(settings.assets_dir / "images").mkdir(parents=True, exist_ok=True)
(settings.assets_dir / "audio").mkdir(parents=True, exist_ok=True)
settings.exports_dir.mkdir(parents=True, exist_ok=True)

db_path = str(settings.db_path)
engine = create_async_engine(
    f"sqlite+aiosqlite:///{db_path}",
    echo=False,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI 依赖注入用"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_async_session() -> AsyncSession:
    """非 FastAPI 上下文用（LangGraph 节点等）"""
    return AsyncSessionLocal()


async def init_db():
    """创建所有表"""
    from sqlalchemy import text

    async with engine.begin() as conn:
        await conn.execute(text("PRAGMA journal_mode=WAL"))
        await conn.execute(text("PRAGMA foreign_keys=ON"))

    # 读 DDL 文件执行——多路径查找
    import os
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "schema.sql"),
        os.path.join(os.getcwd(), "data", "schema.sql"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "schema.sql"),
    ]
    ddl_path = None
    for c in candidates:
        norm = os.path.normpath(c)
        if os.path.exists(norm):
            ddl_path = norm
            break

    if ddl_path:
        with open(ddl_path, "r", encoding="utf-8") as f:
            sql = f.read()
        # 使用 sqlite3 原生连接执行完整 DDL 脚本
        import sqlite3
        db_file = str(settings.db_path)
        conn_raw = sqlite3.connect(db_file)
        try:
            conn_raw.executescript(sql)
        finally:
            conn_raw.close()
    else:
        # 回退：如果找不到 schema.sql，至少创建核心表
        from src.utils.logging_config import logger
        logger.warning("schema.sql not found, creating minimal tables inline")
        await _create_minimal_tables()

    # 初始化单例 user_profile
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id FROM user_profile WHERE id = 1"))
        if result.fetchone() is None:
            await session.execute(text("INSERT INTO user_profile (id) VALUES (1)"))
            await session.commit()


async def _create_minimal_tables():
    """schema.sql 不可用时的最小回退建表"""
    from sqlalchemy import text
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS idea_nodes (
                id TEXT PRIMARY KEY, source_type TEXT NOT NULL DEFAULT 'text',
                raw_content TEXT NOT NULL DEFAULT '', raw_asset_path TEXT,
                standardized_content TEXT, embedding_status TEXT NOT NULL DEFAULT 'pending',
                intent_tags TEXT NOT NULL DEFAULT '[]', context_tags TEXT NOT NULL DEFAULT '[]',
                relevance_score REAL NOT NULL DEFAULT 0.5, completeness_score REAL NOT NULL DEFAULT 0.5,
                actionability_score REAL NOT NULL DEFAULT 0.5,
                status TEXT NOT NULL DEFAULT 'active', merged_into TEXT,
                north_star_relevance REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')), session_id TEXT
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS weaver_sessions (
                id TEXT PRIMARY KEY, north_star TEXT NOT NULL DEFAULT '',
                divergence_degree INTEGER NOT NULL DEFAULT 2,
                status TEXT NOT NULL DEFAULT 'collecting', input_idea_ids TEXT NOT NULL DEFAULT '[]',
                output_design_id TEXT, errors TEXT NOT NULL DEFAULT '[]',
                started_at TEXT NOT NULL DEFAULT (datetime('now')), completed_at TEXT
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS design_documents (
                id TEXT PRIMARY KEY, title TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT 'architecture', source_cluster_ids TEXT NOT NULL DEFAULT '[]',
                content_markdown TEXT NOT NULL DEFAULT '', innovation_score REAL NOT NULL DEFAULT 0.5,
                coherence_score REAL NOT NULL DEFAULT 0.5, feasibility_score REAL NOT NULL DEFAULT 0.5,
                critic_approval INTEGER NOT NULL DEFAULT 0, critic_feedback TEXT,
                version INTEGER NOT NULL DEFAULT 1, parent_design_id TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS concept_clusters (
                id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', description TEXT NOT NULL DEFAULT '',
                member_node_ids TEXT NOT NULL DEFAULT '[]', summary TEXT NOT NULL DEFAULT '',
                innovation_score REAL NOT NULL DEFAULT 0.5, coherence_score REAL NOT NULL DEFAULT 0.5,
                cross_domain_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY, source_node_id TEXT NOT NULL, target_node_id TEXT NOT NULL,
                relationship_type TEXT NOT NULL DEFAULT 'supports',
                strength REAL NOT NULL DEFAULT 0.5, explanation TEXT,
                discovery_method TEXT NOT NULL DEFAULT 'llm_inferred',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_profile (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                frequent_domains TEXT NOT NULL DEFAULT '[]',
                preferred_output_formats TEXT NOT NULL DEFAULT '[]',
                idea_transition_matrix TEXT NOT NULL DEFAULT '{}',
                recurring_constraints TEXT NOT NULL DEFAULT '[]',
                interaction_count INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """))
