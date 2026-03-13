// lib/data/models/container_model.dart
import 'package:json_annotation/json_annotation.dart';
import '../../domain/entities/container.dart';
import 'item_model.dart';
import 'expense_model.dart';

part 'container_model.g.dart';

@JsonSerializable()
class ContainerModel extends Container {
  const ContainerModel({
    required super.id,
    required super.name,
    required super.containerType,
    super.mscContainerNumber,
    required super.allocationMethod,
    required super.ownerId,
    required super.isSealed,
    required super.isShipped,
    required super.allocationOverride,
    super.notes,
    required super.createdAt,
    required super.updatedAt,
    super.items,
    super.expenses,
    super.totalExpenses,
    super.totalWeight,
    super.totalValue,
  });

  factory ContainerModel.fromJson(Map<String, dynamic> json) =>
      _$ContainerModelFromJson(json);

  Map<String, dynamic> toJson() => _$ContainerModelToJson(this);

  Container toEntity() => Container(
        id: id,
        name: name,
        containerType: containerType,
        mscContainerNumber: mscContainerNumber,
        allocationMethod: allocationMethod,
        ownerId: ownerId,
        isSealed: isSealed,
        isShipped: isShipped,
        allocationOverride: allocationOverride,
        notes: notes,
        createdAt: createdAt,
        updatedAt: updatedAt,
        items: items?.map((e) => (e as ItemModel).toEntity()).toList(),
        expenses: expenses?.map((e) => (e as ExpenseModel).toEntity()).toList(),
        totalExpenses: totalExpenses,
        totalWeight: totalWeight,
        totalValue: totalValue,
      );
}

@JsonSerializable()
class CreateContainerRequest {
  final String name;
  
  @JsonKey(name: 'container_type')
  final String containerType;
  
  @JsonKey(name: 'msc_container_number')
  final String? mscContainerNumber;
  
  @JsonKey(name: 'allocation_method')
  final String allocationMethod;
  
  final String? notes;

  const CreateContainerRequest({
    required this.name,
    required this.containerType,
    this.mscContainerNumber,
    this.allocationMethod = 'weight_based',
    this.notes,
  });

  factory CreateContainerRequest.fromJson(Map<String, dynamic> json) =>
      _$CreateContainerRequestFromJson(json);

  Map<String, dynamic> toJson() => _$CreateContainerRequestToJson(this);
}