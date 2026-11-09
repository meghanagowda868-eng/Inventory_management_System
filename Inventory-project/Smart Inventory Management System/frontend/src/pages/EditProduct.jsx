import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { inventoryApi } from '../api/inventoryApi';

export default function EditProduct() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [imageFile, setImageFile] = useState(null);

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: () => inventoryApi.getProduct(id).then(r => r.data),
  });

  const { register, handleSubmit, reset, watch, formState: { errors, isDirty } } = useForm();
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

  useEffect(() => {
    if (product) reset({ ...product, category_id: product.category_id });
  }, [product, reset]);

  const mutation = useMutation({
    mutationFn: (data) => inventoryApi.updateProduct(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['product', id] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['reorders-required'] });
      qc.invalidateQueries({ queryKey: ['reorders-summary'] });
      navigate(`/inventory/${id}`);
    },
  });

  const onSubmit = async (data) => {
    const { id: _id, sku: _sku, category_id: _categoryId, category_name: _categoryName, subcategory_name: _subcategoryName, supplier_name: _supplierName, created_at: _createdAt, updated_at: _updatedAt, stock_status: _stockStatus, is_low_stock: _isLowStock, is_out_of_stock: _isOutOfStock, is_reorder_required: _isReorderRequired, ...updateData } = data;
    let imageUrl = updateData.image_url;
    if (imageFile) {
      const { data: uploaded } = await inventoryApi.uploadImage(imageFile);
      imageUrl = uploaded.image_url;
    }
    mutation.mutate({
      ...updateData,
      subcategory_id: updateData.subcategory_id ? parseInt(updateData.subcategory_id, 10) : undefined,
      supplier_id: updateData.supplier_id ? parseInt(updateData.supplier_id, 10) : null,
      image_url: imageUrl,
      price: parseFloat(updateData.price),
      minimum_stock: parseInt(updateData.minimum_stock, 10),
      reorder_point: parseInt(updateData.reorder_point || 10, 10),
      reorder_quantity: parseInt(updateData.reorder_quantity || 20, 10),
    });
  };

  if (isLoading) return <div className="page-content flex-center" style={{ minHeight: 400 }}><div className="spinner spinner-lg" /></div>;

  return (
    <div className="page-content fade-in" style={{ maxWidth: 720 }}>
      <div className="page-header">
        <h1 className="page-title">Edit Product</h1>
        <p className="page-subtitle">{product?.name} · {product?.sku}</p>
      </div>

      <div className="card p-6">
        {mutation.isError && (
          <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', borderRadius: 'var(--radius-md)', padding: '12px 16px', fontSize: 14, color: 'var(--color-danger)', marginBottom: 20 }}>
            ⚠ {mutation.error?.response?.data?.detail ?? 'Failed to update product'}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 24px' }}>
            <div className="form-group">
              <label className="form-label">Product Name *</label>
              <input className="form-input" {...register('name', { required: 'Name is required' })} />
              {errors.name && <span className="form-error">{errors.name.message}</span>}
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
                <option value="">Select a supplier...</option>
                {suppliers.map((s) => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Brand</label>
              <input className="form-input" {...register('brand')} />
            </div>
            <div className="form-group">
              <label className="form-label">Model Number</label>
              <input className="form-input" {...register('model_number')} />
            </div>
            <div className="form-group">
              <label className="form-label">Selling Price * ($)</label>
              <input type="number" step="0.01" min="0.01" className="form-input"
                {...register('price', { required: 'Price is required', min: { value: 0.01, message: 'Must be > 0' } })} />
              {errors.price && <span className="form-error">{errors.price.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Unit Cost ($)</label>
              <input type="number" step="0.01" min="0.01" className="form-input" placeholder="Optional, for margin planning"
                {...register('unit_cost', { min: { value: 0.01, message: 'Must be greater than 0' }, setValueAs: (value) => value === '' ? null : Number(value) })} />
              {errors.unit_cost && <span className="form-error">{errors.unit_cost.message}</span>}
            </div>
            <div className="form-group">
              <label className="form-label">Minimum Stock Alert</label>
              <input type="number" min="0" className="form-input" {...register('minimum_stock', { min: 0 })} />
            </div>
            <div className="form-group">
              <label className="form-label">⚡ Reorder Point *</label>
              <input type="number" min="0" className="form-input" {...register('reorder_point', { required: 'Reorder point is required', min: 0 })} />
            </div>
            <div className="form-group">
              <label className="form-label">⚡ Reorder Quantity *</label>
              <input type="number" min="1" className="form-input" {...register('reorder_quantity', { required: 'Reorder quantity is required', min: 1 })} />
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Image URL or Upload</label>
              <input className="form-input" {...register('image_url')} />
              <input className="form-input" type="file" accept="image/jpeg,image/png,image/webp,image/gif" style={{ marginTop: 8 }} onChange={(e) => setImageFile(e.target.files?.[0] ?? null)} />
              {imageFile && <span className="form-hint">Selected: {imageFile.name}</span>}
            </div>
            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Description</label>
              <textarea rows={6} className="form-textarea" style={{ minHeight: 120, resize: 'vertical' }} {...register('description')} />
            </div>
          </div>

          <div className="flex-center gap-3 mt-4">
            <button type="button" className="btn btn-secondary" onClick={() => navigate(`/inventory/${id}`)}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={mutation.isPending || !isDirty}>
              {mutation.isPending ? 'Saving...' : '✓ Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
