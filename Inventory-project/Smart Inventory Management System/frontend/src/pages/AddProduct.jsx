import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { inventoryApi } from '../api/inventoryApi';

export default function AddProduct() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [imageFile, setImageFile] = useState(null);

  const { register, handleSubmit, watch, formState: { errors } } = useForm({
    defaultValues: { quantity: 0, minimum_stock: 10, reorder_point: 10, reorder_quantity: 20, price: '', unit_cost: '' },
  });
  const categoryId = watch('category_id');
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((response) => response.data),
  });
  const { data: subcategories = [] } = useQuery({
    queryKey: ['subcategories', categoryId],
    queryFn: () => inventoryApi.listSubcategories(categoryId).then((response) => response.data),
    enabled: Boolean(categoryId),
  });
  const { data: suppliers = [] } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => inventoryApi.listSuppliers().then((response) => response.data),
  });

  const mutation = useMutation({
    mutationFn: (data) => inventoryApi.createProduct(data),
    onSuccess: ({ data }) => {
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['reorders-required'] });
      qc.invalidateQueries({ queryKey: ['reorders-summary'] });
      navigate(`/inventory/${data.id}`);
    },
  });

  const onSubmit = async (data) => {
    let imageUrl = data.image_url;
    if (imageFile) {
      const { data: uploaded } = await inventoryApi.uploadImage(imageFile);
      imageUrl = uploaded.image_url;
    }
    const selectedCategory = categories.find((category) => String(category.id) === String(data.category_id));
    mutation.mutate({
      ...data,
      category: selectedCategory?.name,
      subcategory_id: data.subcategory_id ? parseInt(data.subcategory_id, 10) : undefined,
      supplier_id: data.supplier_id ? parseInt(data.supplier_id, 10) : undefined,
      brand: data.brand || undefined,
      model_number: data.model_number || undefined,
      image_url: imageUrl,
      price: parseFloat(data.price),
      unit_cost: data.unit_cost ? parseFloat(data.unit_cost) : undefined,
      quantity: parseInt(data.quantity, 10),
      minimum_stock: parseInt(data.minimum_stock, 10),
      reorder_point: parseInt(data.reorder_point || 10, 10),
      reorder_quantity: parseInt(data.reorder_quantity || 20, 10),
    });
  };

  return (
    <div className="page-content fade-in" style={{ maxWidth: 720 }}>
      <div className="page-header">
        <h1 className="page-title">Add New Product</h1>
        <p className="page-subtitle">Fill in the product information and reorder replenishment parameters</p>
      </div>

      <div className="card p-6">
        {mutation.isError && (
          <div style={{
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)',
            borderRadius: 'var(--radius-md)', padding: '12px 16px',
            fontSize: 14, color: 'var(--color-danger)', marginBottom: 20,
          }}>
            ⚠ {mutation.error?.response?.data?.detail ?? 'Failed to create product'}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' }}>
            <div className="form-group">
              <label className="form-label">Product Name *</label>
              <input className="form-input" placeholder="e.g. Laptop Pro 15"
                {...register('name', { required: 'Name is required' })} />
              {errors.name && <span className="form-error">{errors.name.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">SKU *</label>
              <input className="form-input" placeholder="e.g. LAPTOP-PRO-15"
                style={{ textTransform: 'uppercase' }}
                {...register('sku', { required: 'SKU is required' })} />
              {errors.sku && <span className="form-error">{errors.sku.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Category *</label>
              <select className="form-input" {...register('category_id', { required: 'Category is required' })}>
                <option value="">Select a category</option>
                {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select>
              {errors.category_id && <span className="form-error">{errors.category_id.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Subcategory *</label>
              <select className="form-input" disabled={!categoryId} {...register('subcategory_id', { required: 'Subcategory is required' })}>
                <option value="">{categoryId ? 'Select a subcategory' : 'Select a category first'}</option>
                {subcategories.map((subcategory) => <option key={subcategory.id} value={subcategory.id}>{subcategory.name}</option>)}
              </select>
              {errors.subcategory_id && <span className="form-error">{errors.subcategory_id.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Primary Supplier</label>
              <select className="form-input" {...register('supplier_id')}>
                <option value="">Select a supplier (optional)...</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Brand</label>
              <input className="form-input" placeholder="e.g. Dell" {...register('brand')} />
            </div>

            <div className="form-group">
              <label className="form-label">Model Number</label>
              <input className="form-input" placeholder="e.g. XPS 13" {...register('model_number')} />
            </div>

            <div className="form-group">
              <label className="form-label">Barcode</label>
              <input className="form-input" placeholder="e.g. 1234567890123"
                {...register('barcode')} />
            </div>

            <div className="form-group">
              <label className="form-label">Selling Price * ($)</label>
              <input type="number" step="0.01" min="0.01" className="form-input" placeholder="0.00"
                {...register('price', { required: 'Price is required', min: { value: 0.01, message: 'Must be > 0' } })} />
              {errors.price && <span className="form-error">{errors.price.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Unit Cost ($)</label>
              <input type="number" step="0.01" min="0.01" className="form-input" placeholder="Procurement cost"
                {...register('unit_cost', { min: { value: 0.01, message: 'Must be greater than 0' } })} />
              {errors.unit_cost && <span className="form-error">{errors.unit_cost.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">Initial Stock Quantity</label>
              <input type="number" min="0" className="form-input" placeholder="0"
                {...register('quantity', { min: 0 })} />
            </div>

            <div className="form-group">
              <label className="form-label">Minimum Stock Alert</label>
              <input type="number" min="0" className="form-input" placeholder="10"
                {...register('minimum_stock', { min: 0 })} />
            </div>

            <div className="form-group">
              <label className="form-label">⚡ Reorder Point *</label>
              <input type="number" min="0" className="form-input" placeholder="10"
                {...register('reorder_point', { required: 'Reorder point is required', min: { value: 0, message: 'Cannot be negative' } })} />
              {errors.reorder_point && <span className="form-error">{errors.reorder_point.message}</span>}
            </div>

            <div className="form-group">
              <label className="form-label">⚡ Reorder Quantity *</label>
              <input type="number" min="1" className="form-input" placeholder="20"
                {...register('reorder_quantity', { required: 'Reorder quantity is required', min: { value: 1, message: 'Must be > 0' } })} />
              {errors.reorder_quantity && <span className="form-error">{errors.reorder_quantity.message}</span>}
            </div>

            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Image URL or Upload</label>
              <input className="form-input" placeholder="https://..."
                {...register('image_url')} />
              <input className="form-input" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style={{ marginTop: 8 }} onChange={(e) => setImageFile(e.target.files?.[0] ?? null)} />
              {imageFile && <span className="form-hint">Selected: {imageFile.name}</span>}
            </div>
          </div>

          <div className="form-group" style={{ gridColumn: '1 / -1' }}>
            <label className="form-label">Description</label>
            <textarea rows={6} className="form-textarea" style={{ minHeight: 120, resize: 'vertical' }} placeholder="Optional product description..."
              {...register('description')} />
          </div>

          <div className="flex-center gap-3 mt-4">
            <button type="button" className="btn btn-secondary" onClick={() => navigate('/inventory')}>
              Cancel
            </button>
            <button
              id="create-product-btn"
              type="submit"
              className="btn btn-primary"
              disabled={mutation.isPending}
            >
              {mutation.isPending ? 'Creating...' : '✓ Create Product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
