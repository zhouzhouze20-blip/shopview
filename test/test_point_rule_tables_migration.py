from pathlib import Path
import unittest


MIGRATION_DIR = Path(__file__).resolve().parents[1] / "python_app" / "alembic" / "versions"


class PointRuleTablesMigrationTest(unittest.TestCase):
    def test_migration_creates_erp_point_rule_tables(self):
        migration_text = "\n".join(path.read_text(encoding="utf-8").lower() for path in MIGRATION_DIR.glob("*.py"))

        for table_name in ("card_paymoderule", "rulejfrate", "sellpaygoods"):
            self.assertIn(f"create table if not exists {table_name}", migration_text)

        self.assertIn("constraint pk_card_paymoderule primary key (jygs, fkcode)", migration_text)
        self.assertIn("constraint pk_rulejfrate primary key (jfseq)", migration_text)
        self.assertIn("constraint pk_sellpaygoods primary key (spgbillno, spgrowno, spggdrow)", migration_text)
        self.assertIn("create index if not exists idx_rulejfrate_custtype", migration_text)
        self.assertIn("create index if not exists idx_rulejfrate_mkt", migration_text)


if __name__ == "__main__":
    unittest.main()
