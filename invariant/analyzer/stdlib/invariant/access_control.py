def should_allow_rbac(data, scope, user, user_roles, role_grants):
    for role in user_roles.get(user, []):
        if role_grants.get(role, {}).get(scope, False):
            return True
    return False
