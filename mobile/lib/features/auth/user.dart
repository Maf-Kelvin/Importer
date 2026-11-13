class AppUser {
  const AppUser({
    required this.id,
    required this.username,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.role,
    required this.isSuperuser,
  });

  final int id;
  final String username;
  final String email;
  final String firstName;
  final String lastName;
  final String role;
  final bool isSuperuser;

  String get displayName {
    final full = '$firstName $lastName'.trim();
    return full.isEmpty ? username : full;
  }

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        id: j['id'] as int,
        username: j['username'] as String,
        email: j['email'] as String,
        firstName: (j['first_name'] as String?) ?? '',
        lastName: (j['last_name'] as String?) ?? '',
        role: (j['role'] as String?) ?? '',
        isSuperuser: (j['is_superuser'] as bool?) ?? false,
      );
}
