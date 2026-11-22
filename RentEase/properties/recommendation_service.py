"""
RentEase AI Recommendation & Behavioral Learning Engine.

Multi-factor intelligent property recommendation service with continuous
behavioral memory. Learns from:
1. Explicit user preferences (budget, location, property type, amenities).
2. Saved / Favorited properties (positive feature vector boosting).
3. Rejected / Dismissed properties ('Not Interested' auto-exclusion & trait suppression).
4. Historical search patterns (fallback bias & latent intent extraction).
"""

from decimal import Decimal
import re
from django.db.models import Q
from .models import Property, PropertyInteraction, UserSearchPreference


# Normalized amenities dictionary for smart synonym matching
AMENITY_SYNONYMS = {
    'wifi': ['wifi', 'wi-fi', 'internet', 'high-speed internet', 'broadband'],
    'ac': ['ac', 'air conditioning', 'air conditioner', 'climate control'],
    'parking': ['parking', 'car parking', 'garage', 'reserved parking'],
    'furnished': ['furnished', 'fully furnished', 'semi-furnished', 'luxury furnishing'],
    'gym': ['gym', 'fitness', 'workout', 'fitness center'],
    'pool': ['pool', 'swimming pool'],
    'balcony': ['balcony', 'terrace', 'patio'],
    'kitchen': ['kitchen', 'modular kitchen', 'cooking', 'equipped kitchen'],
    'security': ['security', 'cctv', '24/7 security', 'gated'],
    'power backup': ['power backup', 'generator', 'inverter', 'ups'],
}

# Type aliases for flexible mapping (e.g. flat -> apartment, room -> studio)
TYPE_ALIASES = {
    'flat': 'apartment',
    'apartments': 'apartment',
    'apartment': 'apartment',
    'house': 'house',
    'villa': 'house',
    'hostel': 'pg',
    'pg': 'pg',
    'pg / hostel': 'pg',
    'room': 'studio',
    'studio': 'studio',
    'farmhouse': 'farmhouse',
    'commercial': 'commercial',
}


def normalize_tokens(text):
    """Clean and tokenize a string for fuzzy token matching."""
    if not text:
        return set()
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(text).lower())
    return {w.strip() for w in cleaned.split() if len(w.strip()) > 1}


def matches_amenity(user_amenity, property_amenity_str):
    """Check if an amenity matches property amenities using synonym expansion."""
    p_norm = property_amenity_str.lower()
    u_norm = user_amenity.strip().lower()

    # Direct substring
    if u_norm in p_norm:
        return True

    # Synonym matching
    for canonical, synonyms in AMENITY_SYNONYMS.items():
        if any(s in u_norm for s in synonyms):
            if any(s in p_norm for s in synonyms):
                return True

    return False


def get_user_interactions(user=None, session_key=None):
    """Retrieve saved, dismissed, and viewed property IDs for a user or session."""
    if not user and not session_key:
        return {'saved': set(), 'dismissed': set(), 'viewed': set()}

    q = Q()
    if user and user.is_authenticated:
        q |= Q(user=user)
    if session_key:
        q |= Q(session_key=session_key)

    interactions = PropertyInteraction.objects.filter(q).select_related('property')
    saved_ids = set()
    dismissed_ids = set()
    viewed_ids = set()
    saved_properties = []
    dismissed_properties = []

    for item in interactions:
        if item.interaction_type == 'saved':
            saved_ids.add(item.property_id)
            saved_properties.append(item.property)
        elif item.interaction_type == 'dismissed':
            dismissed_ids.add(item.property_id)
            dismissed_properties.append(item.property)
        elif item.interaction_type == 'viewed':
            viewed_ids.add(item.property_id)

    return {
        'saved': saved_ids,
        'dismissed': dismissed_ids,
        'viewed': viewed_ids,
        'saved_properties': saved_properties,
        'dismissed_properties': dismissed_properties,
    }


def build_behavioral_profile(saved_properties, dismissed_properties, search_history=None):
    """
    Builds a taste profile from user's saved properties, dismissed listings, and search history.
    Novelty: Learns positive preferences from bookmarks and negative preferences from dismissals.
    """
    profile = {
        'preferred_locations': set(),
        'preferred_types': set(),
        'preferred_amenities': set(),
        'avg_saved_budget': None,
        'dismissed_types': set(),
        'dismissed_locations': set(),
    }

    # 1. Learn from Saved Properties (Positive Weights)
    if saved_properties:
        prices = []
        for prop in saved_properties:
            prices.append(float(prop.rent))
            profile['preferred_types'].add(prop.property_type.lower())
            profile['preferred_locations'].update(normalize_tokens(prop.location))
            for a in prop.get_amenities_list():
                profile['preferred_amenities'].add(a.lower().strip())
        if prices:
            profile['avg_saved_budget'] = sum(prices) / len(prices)

    # 2. Learn from Dismissed Properties (Negative Weights)
    if dismissed_properties:
        for prop in dismissed_properties:
            profile['dismissed_types'].add(prop.property_type.lower())
            profile['dismissed_locations'].update(normalize_tokens(prop.location))

    # 3. Incorporate Search History Tendencies
    if search_history and search_history.exists():
        recent = search_history.first()
        if recent.location:
            profile['preferred_locations'].update(normalize_tokens(recent.location))
        if recent.property_type:
            pt = TYPE_ALIASES.get(recent.property_type.lower(), recent.property_type.lower())
            profile['preferred_types'].add(pt)
        if recent.target_budget and not profile['avg_saved_budget']:
            profile['avg_saved_budget'] = float(recent.target_budget)

    return profile


def calculate_property_score(property_obj, target_budget, preferred_location,
                             preferred_type, requested_amenities, behavioral_profile):
    """
    Computes a composite AI match score (0.0 to 1.0) and generates explanatory reasoning tags.
    """
    reasons = []
    daily_rent = float(property_obj.rent)

    # -------------------------------------------------------------------------
    # 1. Budget Fit Score (Weight: 30%)
    # -------------------------------------------------------------------------
    budget_score = 0.8  # neutral baseline
    effective_budget = target_budget or behavioral_profile.get('avg_saved_budget')

    if effective_budget and effective_budget > 0:
        ratio = daily_rent / effective_budget
        if 0.85 <= ratio <= 1.05:
            budget_score = 1.0
            reasons.append(f"🎯 Perfect budget match (₹{daily_rent:,.0f}/day vs ₹{effective_budget:,.0f} target)")
        elif ratio < 0.85:
            savings_pct = int((1.0 - ratio) * 100)
            budget_score = max(0.70, 1.0 - (0.85 - ratio) * 0.4)
            reasons.append(f"💰 Great value: ₹{daily_rent:,.0f}/day ({savings_pct}% below your budget)")
        elif 1.05 < ratio <= 1.25:
            overage = int((ratio - 1.0) * 100)
            budget_score = max(0.50, 1.0 - (ratio - 1.0) * 1.8)
            reasons.append(f"⚖️ Slightly above budget (+{overage}%) with premium features")
        else:
            budget_score = max(0.10, 1.0 - (ratio - 1.0) * 0.9)
    else:
        reasons.append(f"💵 Competitive daily rate of ₹{daily_rent:,.0f}/day")

    # -------------------------------------------------------------------------
    # 2. Location Match Score (Weight: 25%)
    # -------------------------------------------------------------------------
    location_score = 0.7  # neutral
    prop_loc_tokens = normalize_tokens(property_obj.location)

    if preferred_location:
        user_loc_tokens = normalize_tokens(preferred_location)
        overlap = prop_loc_tokens.intersection(user_loc_tokens)
        if overlap:
            overlap_ratio = len(overlap) / max(1, len(user_loc_tokens))
            location_score = min(1.0, 0.6 + overlap_ratio * 0.4)
            matched_words = ", ".join(w.capitalize() for w in overlap)
            reasons.append(f"📍 Prime location match in {matched_words}")
        else:
            location_score = 0.25
    elif behavioral_profile['preferred_locations']:
        # Learned location preference from saved properties
        overlap = prop_loc_tokens.intersection(behavioral_profile['preferred_locations'])
        if overlap:
            location_score = 0.90
            reasons.append(f"📍 In {property_obj.location} (similar to your saved stays)")

    # -------------------------------------------------------------------------
    # 3. Property Type Alignment (Weight: 20%)
    # -------------------------------------------------------------------------
    type_score = 0.75
    prop_type = property_obj.property_type.lower()

    if preferred_type and preferred_type != 'all':
        norm_user_type = TYPE_ALIASES.get(preferred_type.lower(), preferred_type.lower())
        if prop_type == norm_user_type:
            type_score = 1.0
            reasons.append(f"🏡 Matches requested type: {property_obj.get_property_type_display()}")
        elif (norm_user_type in ['apartment', 'studio'] and prop_type in ['apartment', 'studio']) or \
             (norm_user_type in ['house', 'farmhouse'] and prop_type in ['house', 'farmhouse']):
            type_score = 0.65
        else:
            type_score = 0.20
    elif prop_type in behavioral_profile['preferred_types']:
        type_score = 0.95
        reasons.append(f"🏡 {property_obj.get_property_type_display()} matches your favorite style")

    # -------------------------------------------------------------------------
    # 4. Amenities Overlap Score (Weight: 25%)
    # -------------------------------------------------------------------------
    amenities_score = 0.75
    prop_amenities_raw = property_obj.amenities or ''
    matched_amenity_names = []

    if requested_amenities:
        matched_count = 0
        for am in requested_amenities:
            if matches_amenity(am, prop_amenities_raw):
                matched_count += 1
                matched_amenity_names.append(am.strip())

        if requested_amenities:
            amenities_score = matched_count / len(requested_amenities)
            if matched_amenity_names:
                amenity_list_str = ", ".join(matched_amenity_names[:3])
                reasons.append(f"⚡ Includes {len(matched_amenity_names)} of your amenities: {amenity_list_str}")
    else:
        # Check against learned preferences from saved properties
        prop_amenities_list = [a.lower().strip() for a in property_obj.get_amenities_list()]
        saved_overlap = behavioral_profile['preferred_amenities'].intersection(prop_amenities_list)
        if saved_overlap:
            amenities_score = 0.90
            top_common = ", ".join(w.title() for w in list(saved_overlap)[:3])
            reasons.append(f"✨ Features amenities you love: {top_common}")

    # Explicit subtotal
    base_score = (
        (0.30 * budget_score) +
        (0.25 * location_score) +
        (0.20 * type_score) +
        (0.25 * amenities_score)
    )

    # -------------------------------------------------------------------------
    # 5. Behavioral Learning Adjustments (Novelty)
    # -------------------------------------------------------------------------
    behavior_modifier = 0.0

    # Positive Boost: Saved history match
    if behavioral_profile['preferred_types'] and prop_type in behavioral_profile['preferred_types']:
        behavior_modifier += 0.08
    if behavioral_profile['preferred_locations'] and prop_loc_tokens.intersection(behavioral_profile['preferred_locations']):
        behavior_modifier += 0.08

    # Negative Penalty: Similar traits to rejected/dismissed properties
    if behavioral_profile['dismissed_types'] and prop_type in behavioral_profile['dismissed_types']:
        behavior_modifier -= 0.15
    if behavioral_profile['dismissed_locations'] and prop_loc_tokens.intersection(behavioral_profile['dismissed_locations']):
        behavior_modifier -= 0.15

    # Star rating quality boost
    avg_rating = property_obj.average_rating()
    if avg_rating and avg_rating >= 4.5:
        behavior_modifier += 0.05
        reasons.append(f"⭐ Highly rated by verified guests ({avg_rating} ★)")

    # Composite score with bounds
    final_score = base_score + behavior_modifier
    int_score = int(round(final_score * 100))
    int_score = max(45, min(99, int_score))

    # Keep reasons clean and concise (max 3 bullets)
    clean_reasons = []
    for r in reasons:
        if r not in clean_reasons:
            clean_reasons.append(r)
        if len(clean_reasons) >= 3:
            break

    if not clean_reasons:
        clean_reasons = [
            f"🏡 {property_obj.get_property_type_display()} in {property_obj.location}",
            f"💵 Affordable daily rate ₹{daily_rent:,.0f}/day"
        ]

    return int_score, clean_reasons


def get_ai_recommendations(user=None, session_key=None, target_budget=None,
                           preferred_location=None, preferred_type=None,
                           requested_amenities=None, limit=9):
    """
    Main entry point: Generates personalized AI property recommendations.

    Steps:
    1. Retrieves user's interaction history (saved, dismissed).
    2. Excludes dismissed/rejected properties directly (Novelty).
    3. Builds behavioral taste profile (saved boost, rejected penalty).
    4. Evaluates all active available properties against explicit + learned vectors.
    5. Returns ranked list with match percentages and explainable AI reasons.
    """
    # 1. Fetch user interactions
    interactions = get_user_interactions(user=user, session_key=session_key)
    saved_ids = interactions['saved']
    dismissed_ids = interactions['dismissed']

    # 2. Candidate properties: Available properties, excluding dismissed ones
    candidates = Property.objects.filter(is_available=True)
    if dismissed_ids:
        candidates = candidates.exclude(id__in=dismissed_ids)

    # 3. Build behavioral learning profile
    search_history = None
    if user and user.is_authenticated:
        search_history = UserSearchPreference.objects.filter(user=user)
    elif session_key:
        search_history = UserSearchPreference.objects.filter(session_key=session_key)

    behavioral_profile = build_behavioral_profile(
        saved_properties=interactions['saved_properties'],
        dismissed_properties=interactions['dismissed_properties'],
        search_history=search_history
    )

    # Parse requested amenities
    if isinstance(requested_amenities, str):
        requested_amenities = [a.strip() for a in requested_amenities.split(',') if a.strip()]
    elif not requested_amenities:
        requested_amenities = []

    # Clean target budget
    budget_float = None
    if target_budget:
        try:
            budget_float = float(target_budget)
        except (ValueError, TypeError):
            pass

    # 4. Score all candidates
    scored_results = []
    for prop in candidates:
        score, reasons = calculate_property_score(
            property_obj=prop,
            target_budget=budget_float,
            preferred_location=preferred_location,
            preferred_type=preferred_type,
            requested_amenities=requested_amenities,
            behavioral_profile=behavioral_profile
        )

        scored_results.append({
            'property': prop,
            'score': score,
            'reasons': reasons,
            'is_saved': prop.id in saved_ids,
            'is_booked': prop.is_booked,
            'is_currently_available': prop.is_currently_available,
        })

    # Sort descending by AI Match Score
    scored_results.sort(key=lambda x: x['score'], reverse=True)

    # Return top N
    return {
        'recommendations': scored_results[:limit],
        'total_evaluated': len(scored_results),
        'saved_count': len(saved_ids),
        'dismissed_count': len(dismissed_ids),
        'behavioral_profile': behavioral_profile,
    }
