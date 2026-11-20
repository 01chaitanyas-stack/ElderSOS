import pytest
import json
from app import create_app
from models import db, User, DietProfile, Allergy, MealPlan
from config import Config
from services.diet_engine import DietEngine

class TestDietConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"

@pytest.fixture
def diet_app_client():
    app = create_app(TestDietConfig)
    with app.app_context():
        db.create_all()
        user = User(name="Senior Anandi", email="anandi@example.com", age=74)
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        # Setup Diet Profile
        profile = DietProfile(
            user_id=user.id,
            diet_type="veg",
            dislikes="papaya, peanuts",
            restrictions="low-sodium, soft-food",
            conditions_note="Type 2 Diabetes, Hypertension",
            clinician_note="Limit salt to under 4g per day"
        )
        # Add Allergies
        a1 = Allergy(user_id=user.id, name="dairy")
        a2 = Allergy(user_id=user.id, name="mustard")
        
        db.session.add_all([profile, a1, a2])
        db.session.commit()

        client = app.test_client()
        client.post("/login", data={"email": "anandi@example.com", "password": "pass123"})
        
        yield client, user, app
        db.session.remove()
        db.drop_all()

def test_engine_strict_allergen_and_dislike_filtering():
    engine = DietEngine()
    
    # 1. User allergic to dairy and mustard, dislikes papaya
    filtered = engine.filter_meals(
        diet_type="veg",
        allergies=["dairy", "mustard"],
        dislikes=["papaya"],
        restrictions=[]
    )
    
    assert len(filtered) > 0
    for meal in filtered:
        # Must not contain allergens
        assert "dairy" not in [a.lower() for a in meal.get("allergies", [])]
        assert "mustard" not in [a.lower() for a in meal.get("allergies", [])]
        # Must not have cow dairy in ingredients
        assert not any("cow milk" in ing.lower() or "paneer" in ing.lower() or "curd" in ing.lower() for ing in meal.get("ingredients", []))
        # Must not be papaya
        assert "papaya" not in meal.get("name", "").lower()
        # Must not be non-veg
        assert meal.get("diet_type") != "non-veg"

def test_engine_vegan_filter():
    engine = DietEngine()
    filtered = engine.filter_meals(diet_type="vegan")
    assert len(filtered) > 0
    for meal in filtered:
        assert meal.get("diet_type") == "vegan"

def test_generate_daily_plan_structure(diet_app_client):
    client, user, app = diet_app_client
    
    with app.app_context():
        u = db.session.get(User, user.id)
        engine = DietEngine()
        plan = engine.generate_daily_plan(u, "2026-10-26")
        
        assert "meals" in plan
        assert "breakfast" in plan["meals"]
        assert "lunch" in plan["meals"]
        assert "evening_snacks" in plan["meals"]
        assert "dinner" in plan["meals"]
        
        # Verify structure of each meal
        for mtype in ["breakfast", "lunch", "evening_snacks", "dinner"]:
            m = plan["meals"][mtype]
            assert "name" in m
            assert "portion_size" in m
            assert "ingredients" in m
            assert "calories" in m
            
        # Verify medical disclaimer and condition notices
        assert "Medical Notice:" in plan["medical_disclaimer"]
        assert "Type 2 Diabetes" in plan["condition_notice"]
        assert "Limit salt" in plan["clinician_note"]
        assert plan["nutrition_totals"]["calories"] > 0

def test_diet_routes(diet_app_client):
    client, user, app = diet_app_client
    
    # 1. View diet page (should auto-generate today's plan)
    res = client.get("/diet/")
    assert res.status_code == 200
    assert b"Daily Senior Nutrition Plan" in res.data
    assert b"Medical Condition Notice" in res.data
    
    # 2. Regenerate plan
    res_gen = client.post("/diet/generate", follow_redirects=True)
    assert res_gen.status_code == 200
    assert b"Fresh personalized daily meal plan successfully generated" in res_gen.data
    
    # 3. View history
    res_hist = client.get("/diet/history")
    assert res_hist.status_code == 200
    assert b"Past Meal Plan History" in res_hist.data
