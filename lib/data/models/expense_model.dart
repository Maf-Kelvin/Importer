// lib/data/models/expense_model.dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/expense.dart';

part 'expense_model.g.dart';

@JsonSerializable()
class ExpenseModel extends Expense {
  const ExpenseModel({
    required super.id,
    required super.containerId,
    required super.expenseType,
    required super.amount,
    required super.currency,
    super.description,
    required super.fxRateToUsd,
    required super.amountUsd,
    required super.createdAt,
    required super.updatedAt,
  });

  factory ExpenseModel.fromJson(Map<String, dynamic> json) =>
      _$ExpenseModelFromJson(json);

  Map<String, dynamic> toJson() => _$ExpenseModelToJson(this);

  Expense toEntity() => Expense(
        id: id,
        containerId: containerId,
        expenseType: expenseType,
        amount: amount,
        currency: currency,
        description: description,
        fxRateToUsd: fxRateToUsd,
        amountUsd: amountUsd,
        createdAt: createdAt,
        updatedAt: updatedAt,
      );
}

@JsonSerializable()
class CreateExpenseRequest {
  @JsonKey(name: 'container_id')
  final int containerId;
  
  @JsonKey(name: 'expense_type')
  final String expenseType;
  
  final double amount;
  final String currency;
  final String? description;

  const CreateExpenseRequest({
    required this.containerId,
    required this.expenseType,
    required this.amount,
    required this.currency,
    this.description,
  });

  factory CreateExpenseRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateExpenseRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CreateExpenseRequestToJson(this);
}
