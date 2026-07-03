# 🎓 Learning Management & Prerequisite Tracking System (LMPTS)

## 📌 Project Overview

The **Learning Management & Prerequisite Tracking System (LMPTS)** is a Python-based application designed to manage educational courses, prerequisite relationships, learner enrollments, and learning path recommendations.

The system enforces prerequisite constraints, prevents circular dependencies, tracks learner progress, computes learning paths using graph algorithms, and provides analytics through an interactive graphical user interface.

This project demonstrates the practical application of:

* Object-Oriented Programming (OOP)
* Data Structures & Algorithms
* Design Patterns
* Database Design
* Software Engineering Principles
* Automated Testing
* GUI Development

---

# 🎯 Problem Statement

Educational institutions and training organizations often struggle with managing complex prerequisite structures. Existing systems typically:

* Allow invalid enrollments
* Fail to detect circular dependencies
* Lack learning path recommendations
* Provide limited analytics
* Are difficult to extend and maintain

LMPTS addresses these challenges by providing a modular, extensible, and intelligent prerequisite management system.

---

# ✨ Features

## 🔐 Authentication System

* Secure login system
* Role-based authentication
* Password hashing using bcrypt
* Session management
* User registration

### Supported Roles

* Administrator
* Learner
* Instructor
* Analyst

---

## 📚 Course Management

* Create courses
* Update course information
* Delete courses
* Publish/archive courses
* View course catalog

---

## 🔗 Prerequisite Management

* Add prerequisite relationships
* Remove prerequisite relationships
* View direct prerequisites
* View transitive prerequisites
* Detect circular dependencies

---

## 👨‍🎓 Learner Management

* Register learners
* Track learner progress
* View completed courses
* View enrolled courses
* Calculate completion rates

---

## 📝 Enrollment System

* Enroll learners
* Validate prerequisites
* Prevent duplicate enrollment
* Mark course completion
* Assign scores

---

## 🛣 Learning Path Recommendation

* Compute shortest learning path
* Validate learning sequences
* Calculate path statistics
* Generate course recommendations

---

## 📊 Analytics Dashboard

* Course completion statistics
* Learner performance metrics
* Bottleneck course detection
* System-wide statistics
* Prerequisite complexity analysis

---

# 🏗 System Architecture

The project follows a layered architecture:

```text
GUI Layer
    ↓
Service Layer
    ↓
Repository Layer
    ↓
Database Layer
```

### Components

```text
lmpts_project/

├── core/
├── auth/
├── algorithms/
├── repository/
├── services/
├── gui/
├── tests/
├── data/
└── docs/
```

---

# 🧠 OOP Concepts Implemented

* Encapsulation
* Inheritance
* Polymorphism
* Abstraction
* Composition

---

# 🏛 Design Patterns Used

| Pattern            | Implementation              |
| ------------------ | --------------------------- |
| Repository Pattern | Database abstraction        |
| Factory Pattern    | Object creation             |
| Strategy Pattern   | Learning path algorithms    |
| Observer Pattern   | Progress tracking           |
| Singleton Pattern  | Database connection/session |

---

# 📈 Data Structures & Algorithms

## Data Structures

* Directed Graph
* Hash Maps
* Sets
* Queues
* Trees

## Algorithms

* DFS Cycle Detection
* Breadth First Search (BFS)
* Graph Traversal
* Learning Path Computation
* Complexity Analysis

---

# 💾 Database

Database: SQLite

Main Tables:

```sql
users
courses
learners
enrollments
prerequisites
course_progress
analytics
```

---

# 🔒 Security Features

* Password hashing using bcrypt
* Role-based access control
* Session management
* Input validation
* SQL injection prevention
* Authentication validation

---

# 🖥 User Interface

The graphical interface is built using Tkinter.

### Screens

* Login Window
* Admin Dashboard
* Learner Dashboard
* Enrollment Portal
* Analytics Dashboard

---

# 🧪 Testing

Testing framework:

* pytest
* pytest-cov

Testing includes:

* Unit Tests
* Integration Tests
* Edge Case Tests

Target Coverage:

```text
80%+
```

---

# ⚙️ Installation

Clone the repository:

```bash
git clone <repository-url>
cd lmpts_project
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

Windows:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# ▶️ Running the Application

```bash
python main.py
```

---

# 🧪 Running Tests

```bash
pytest
```

Generate coverage report:

```bash
pytest --cov
```

---

# 📋 Example Workflow

### Administrator

1. Login
2. Create courses
3. Add prerequisites
4. Validate prerequisite graph

### Learner

1. Register/Login
2. View available courses
3. Enroll in courses
4. Complete prerequisites
5. Progress through learning path

### Analyst

1. Login
2. View analytics
3. Analyze bottleneck courses
4. Generate reports

---

# 👥 Team Members

| Member   | Responsibility               |
| -------- | ---------------------------- |
| Member 1 | Core Models & Authentication |
| Member 2 | Algorithms & Graphs          |
| Member 3 | Database & Repository        |
| Member 4 | Services & Business Logic    |
| Member 5 | GUI Development              |
| Member 6 | Testing & Documentation      |

---

# 📚 Technologies Used

* Python 3.x
* SQLite
* Tkinter
* bcrypt
* pytest
* Git
* GitHub

---

# 🚀 Future Enhancements

* PostgreSQL Support
* Flask REST API
* React Frontend
* Email Notifications
* AI-based Recommendations
* Docker Deployment
* Cloud Hosting

---

# 🏆 Project Objectives Achieved

* ✅ Object-Oriented Programming
* ✅ Design Patterns
* ✅ Graph Algorithms
* ✅ Database Design
* ✅ Authentication
* ✅ GUI Development
* ✅ Testing
* ✅ Analytics
* ✅ Software Engineering Principles
