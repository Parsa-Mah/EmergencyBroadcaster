
from sqlalchemy import create_engine, String, Integer, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from tabulate import tabulate

# 1. Setup the Database Connection (The Engine)
# Replace user, password, and dbname with your actual credentials
DATABASE_URL = "postgresql+psycopg2://postgres:1234@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

# 2. Define the Base Class (The foundation for our models)
class Base(DeclarativeBase):
    pass

# 3. Define the Model (The Table)
class Employee(Base):
    __tablename__ = "employees_orm"

    # 'mapped_column' is the modern way to define columns in SQLAlchemy 2.0
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    salary: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String(100), nullable=True)  # New Column!

    def __repr__(self) -> str:
        return f"Employee(id={self.id}, name={self.name})"

def init_db_and_insert():
    # Create tables in the DB (IF NOT EXISTS)
    Base.metadata.create_all(engine)
    print("Table 'employees_orm' created successfully.")

    # Open a Session to interact with the DB
    with Session(engine) as session:
        # Create Python Objects
        emp1 = Employee(name="Alice Smith", role="Software Engineer", salary=85000)
        emp2 = Employee(name="Bob Jones", role="Data Scientist", salary=90000)
        emp3 = Employee(name="Charlie Brown", role="Project Manager", salary=95000)

        # Add to the session and commit (save) to DB
        session.add_all([emp1, emp2, emp3])
        session.commit()
        print("Data inserted successfully.")


def display_data():
    with Session(engine) as session:
        # Construct the query: "SELECT * FROM employees_orm"
        stmt = select(Employee)

        # Execute and get all results
        # .scalars() extracts the ORM objects from the result rows
        employees = session.execute(stmt).scalars().all()

        print("-" * 60)
        print(f"{'ID':<5} {'Name':<20} {'Role':<20} {'Salary':<10}")
        print("-" * 60)

        for emp in employees:
            # Notice we access data using .dot notation (emp.name), not dictionary keys!
            print(f"{emp.id:<5} {emp.name:<20} {emp.role:<20} ${emp.salary:<10}")

        print("-" * 60)

def display_with_tabulate():
    with Session(engine) as session:
        stmt = select(Employee)
        employees = session.execute(stmt).scalars().all()

        # 1. Convert Objects to a List of Lists
        # We explicitly choose which fields to display
        data = [[emp.id, emp.name, emp.role, emp.salary] for emp in employees]

        # 2. Define Headers
        headers = ["ID", "Name", "Role", "Salary"]

        # 3. Print
        print(tabulate(data, headers=headers, tablefmt="psql"))


if __name__ == "__main__":
    display_with_tabulate()