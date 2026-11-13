class Customer {
  const Customer({required this.id, required this.name, this.email, this.phone});

  final int id;
  final String name;
  final String? email;
  final String? phone;

  factory Customer.fromJson(Map<String, dynamic> j) => Customer(
        id: j['id'] as int,
        name: j['name'] as String,
        email: j['email'] as String?,
        phone: j['phone'] as String?,
      );
}
