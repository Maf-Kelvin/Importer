// lib/presentation/screens/containers/create_container_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:go_router/go_router.dart';
import '../../widgets/common/custom_button.dart';
import '../../widgets/common/custom_text_field.dart';
import '../../../core/utils/validators.dart';
import '../../../core/constants/app_constants.dart';

class CreateContainerScreen extends ConsumerStatefulWidget {
  const CreateContainerScreen({super.key});

  @override
  ConsumerState<CreateContainerScreen> createState() => _CreateContainerScreenState();
}

class _CreateContainerScreenState extends ConsumerState<CreateContainerScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _mscNumberController = TextEditingController();
  final _notesController = TextEditingController();
  
  String _selectedType = '20ft';
  String _allocationMethod = 'weight_based';
  bool _isLoading = false;

  @override
  void dispose() {
    _nameController.dispose();
    _mscNumberController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Create Container'),
        actions: [
          TextButton(
            onPressed: _isLoading ? null : _handleSave,
            child: _isLoading
                ? SizedBox(
                    width: 16.w,
                    height: 16.w,
                    child: const CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Save'),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: EdgeInsets.all(16.w),
          children: [
            // Container name
            CustomTextField(
              controller: _nameController,
              labelText: 'Container Name *',
              hintText: 'e.g., CONT-2024-001',
              validator: (value) => Validators.required(value, 'Container name'),
              enabled: !_isLoading,
            ),
            SizedBox(height: 16.h),

            // Container type
            Text(
              'Container Type *',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            SizedBox(height: 8.h),
            SegmentedButton<String>(
              segments: AppConstants.containerTypes
                  .map((type) => ButtonSegment(
                        value: type,
                        label: Text('$type Container'),
                      ))
                  .toList(),
              selected: {_selectedType},
              onSelectionChanged: _isLoading ? null : (value) {
                setState(() {
                  _selectedType = value.first;
                });
              },
            ),
            SizedBox(height: 16.h),

            // MSC container number
            CustomTextField(
              controller: _mscNumberController,
              labelText: 'MSC Container Number',
              hintText: 'e.g., MSCU123456789',
              prefixIcon: Icons.local_shipping_outlined,
              enabled: !_isLoading,
            ),
            SizedBox(height: 16.h),

            // Cost allocation method
            Text(
              'Cost Allocation Method *',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            SizedBox(height: 8.h),
            Column(
              children: [
                RadioListTile<String>(
                  title: const Text('Weight-based'),
                  subtitle: const Text('Allocate costs based on item weight'),
                  value: 'weight_based',
                  groupValue: _allocationMethod,
                  onChanged: _isLoading ? null : (value) {
                    setState(() {
                      _allocationMethod = value!;
                    });
                  },
                ),
                RadioListTile<String>(
                  title: const Text('Value-based'),
                  subtitle: const Text('Allocate costs based on item purchase value'),
                  value: 'value_based',
                  groupValue: _allocationMethod,
                  onChanged: _isLoading ? null : (value) {
                    setState(() {
                      _allocationMethod = value!;
                    });
                  },
                ),
              ],
            ),
            SizedBox(height: 16.h),

            // Notes
            CustomTextField(
              controller: _notesController,
              labelText: 'Notes',
              hintText: 'Additional notes about this container',
              maxLines: 3,
              enabled: !_isLoading,
            ),
            SizedBox(height: 32.h),

            // Create button
            CustomButton(
              onPressed: _isLoading ? null : _handleSave,
              child: _isLoading
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                          ),
                        ),
                        SizedBox(width: 12),
                        Text('Creating...'),
                      ],
                    )
                  : const Text('Create Container'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleSave() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
    });

    try {
      // Create container logic here
      await Future.delayed(const Duration(seconds: 2)); // Mock delay

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Container created successfully!'),
            backgroundColor: Colors.green,
          ),
        );
        context.pop(); // Go back to container list
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to create container: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }
}