// frontend/src/components/ops/business-form.tsx
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import {
  type Business,
  type BusinessFormValues as BusinessPayload,
  type DayHours,
  listCategories,
  listLocalities,
} from "@/lib/ops-api";

const DAYS = [
  { index: 0, label: "Mon" },
  { index: 1, label: "Tue" },
  { index: 2, label: "Wed" },
  { index: 3, label: "Thu" },
  { index: 4, label: "Fri" },
  { index: 5, label: "Sat" },
  { index: 6, label: "Sun" },
];

const dayHoursSchema = z.object({
  closed: z.boolean(),
  open_time: z.string(),
  close_time: z.string(),
});

const schema = z.object({
  region_id: z.uuid(),
  locality_id: z.uuid(),
  name_mr: z.string().min(1),
  name_en: z.string().min(1),
  owner_name: z.string().min(1),
  category_ids: z.array(z.uuid()).min(1, "pick at least one category"),
  contact_numbers: z.string().min(1),
  whatsapp_number: z.string(),
  landmark: z.string(),
  latitude: z.number().min(-90).max(90),
  longitude: z.number().min(-180).max(180),
  attributes: z.string(),
  opening_hours: z.record(z.string(), dayHoursSchema),
});

export type BusinessFormInput = z.infer<typeof schema>;

function defaultOpeningHours(): BusinessFormInput["opening_hours"] {
  const hours: BusinessFormInput["opening_hours"] = {};
  for (const day of DAYS) {
    hours[day.index] = { closed: false, open_time: "09:00", close_time: "21:00" };
  }
  return hours;
}

function toFormValues(business: Business): BusinessFormInput {
  const hours: BusinessFormInput["opening_hours"] = {};
  for (const day of DAYS) {
    const d = business.opening_hours[day.index];
    hours[day.index] = d?.open_time
      ? { closed: false, open_time: d.open_time.slice(0, 5), close_time: (d.close_time ?? "").slice(0, 5) }
      : { closed: true, open_time: "09:00", close_time: "21:00" };
  }
  return {
    region_id: business.region_id,
    locality_id: business.locality_id,
    name_mr: business.name_mr,
    name_en: business.name_en,
    owner_name: business.owner_name,
    category_ids: business.category_ids,
    contact_numbers: business.contact_numbers.join(", "),
    whatsapp_number: business.whatsapp_number ?? "",
    landmark: business.landmark,
    latitude: business.latitude,
    longitude: business.longitude,
    attributes: business.attributes.join(", "),
    opening_hours: hours,
  };
}

function toSubmitValues(values: BusinessFormInput): BusinessPayload {
  const opening_hours: Record<number, DayHours> = {};
  for (const day of DAYS) {
    const d = values.opening_hours[day.index];
    opening_hours[day.index] = d.closed
      ? { open_time: null, close_time: null, midday_break_start: null, midday_break_end: null }
      : {
          open_time: `${d.open_time}:00`,
          close_time: `${d.close_time}:00`,
          midday_break_start: null,
          midday_break_end: null,
        };
  }
  return {
    region_id: values.region_id,
    locality_id: values.locality_id,
    name_mr: values.name_mr,
    name_en: values.name_en,
    owner_name: values.owner_name,
    category_ids: values.category_ids,
    contact_numbers: values.contact_numbers.split(",").map((s) => s.trim()).filter(Boolean),
    whatsapp_number: values.whatsapp_number.trim() || null,
    landmark: values.landmark,
    latitude: values.latitude,
    longitude: values.longitude,
    opening_hours,
    attributes: values.attributes.split(",").map((s) => s.trim()).filter(Boolean),
  };
}

export function BusinessForm({
  existing,
  onSubmit,
  pending,
  submitLabel,
}: {
  existing?: Business;
  onSubmit: (values: BusinessPayload) => void;
  pending: boolean;
  submitLabel: string;
}) {
  const {
    register,
    handleSubmit,
    control,
    watch,
    setValue,
    formState: { errors },
  } = useForm<BusinessFormInput>({
    resolver: zodResolver(schema),
    defaultValues: existing
      ? toFormValues(existing)
      : {
          region_id: "",
          locality_id: "",
          name_mr: "",
          name_en: "",
          owner_name: "",
          category_ids: [],
          contact_numbers: "",
          whatsapp_number: "",
          landmark: "",
          latitude: 21.15,
          longitude: 74.33,
          attributes: "",
          opening_hours: defaultOpeningHours(),
        },
  });

  const regionId = watch("region_id");
  const categoriesQuery = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const localitiesQuery = useQuery({
    queryKey: ["localities", regionId],
    queryFn: () => listLocalities(regionId),
    enabled: schema.shape.region_id.safeParse(regionId).success,
  });

  function copyMondayToAll() {
    const monday = watch("opening_hours.0");
    for (const day of DAYS.slice(1)) {
      setValue(`opening_hours.${day.index}`, { ...monday });
    }
  }

  return (
    <form
      onSubmit={handleSubmit((values) => onSubmit(toSubmitValues(values)))}
      className="flex max-w-2xl flex-col gap-3 text-sm"
    >
      <div className="grid grid-cols-2 gap-3">
        <Field label="Region ID" error={errors.region_id?.message}>
          <input
            {...register("region_id")}
            disabled={Boolean(existing)}
            className="h-9 w-full rounded border border-input px-2 disabled:bg-muted"
          />
        </Field>
        <Field label="Locality" error={errors.locality_id?.message}>
          <select {...register("locality_id")} className="h-9 w-full rounded border border-input px-2">
            <option value="">select...</option>
            {localitiesQuery.data?.map((loc) => (
              <option key={loc.id} value={loc.id}>
                {loc.name_mr} ({loc.name_en})
              </option>
            ))}
          </select>
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Name (Marathi)" error={errors.name_mr?.message}>
          <input {...register("name_mr")} className="h-9 w-full rounded border border-input px-2" />
        </Field>
        <Field label="Name (English)" error={errors.name_en?.message}>
          <input {...register("name_en")} className="h-9 w-full rounded border border-input px-2" />
        </Field>
      </div>

      <Field label="Owner name" error={errors.owner_name?.message}>
        <input {...register("owner_name")} className="h-9 w-full rounded border border-input px-2" />
      </Field>

      <Field label="Categories" error={errors.category_ids?.message}>
        <Controller
          control={control}
          name="category_ids"
          render={({ field }) => (
            <div className="flex flex-wrap gap-3">
              {categoriesQuery.data?.map((cat) => (
                <label key={cat.id} className="flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={field.value.includes(cat.id)}
                    onChange={(e) => {
                      field.onChange(
                        e.target.checked
                          ? [...field.value, cat.id]
                          : field.value.filter((id) => id !== cat.id),
                      );
                    }}
                  />
                  {cat.name_en}
                </label>
              ))}
            </div>
          )}
        />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Contact numbers (comma-separated)" error={errors.contact_numbers?.message}>
          <input
            {...register("contact_numbers")}
            className="h-9 w-full rounded border border-input px-2"
          />
        </Field>
        <Field label="WhatsApp number">
          <input
            {...register("whatsapp_number")}
            className="h-9 w-full rounded border border-input px-2"
          />
        </Field>
      </div>

      <Field label="Landmark">
        <input {...register("landmark")} className="h-9 w-full rounded border border-input px-2" />
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Latitude" error={errors.latitude?.message}>
          <input
            type="number"
            step="any"
            {...register("latitude", { valueAsNumber: true })}
            className="h-9 w-full rounded border border-input px-2"
          />
        </Field>
        <Field label="Longitude" error={errors.longitude?.message}>
          <input
            type="number"
            step="any"
            {...register("longitude", { valueAsNumber: true })}
            className="h-9 w-full rounded border border-input px-2"
          />
        </Field>
      </div>

      <Field label="Attributes (comma-separated)">
        <input {...register("attributes")} className="h-9 w-full rounded border border-input px-2" />
      </Field>

      <div>
        <div className="mb-1 flex items-center justify-between">
          <span className="font-semibold">Opening hours</span>
          <button
            type="button"
            onClick={copyMondayToAll}
            className="text-xs text-primary hover:underline"
          >
            copy Monday to all days
          </button>
        </div>
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="pb-1">Day</th>
              <th className="pb-1">Closed</th>
              <th className="pb-1">Open</th>
              <th className="pb-1">Close</th>
            </tr>
          </thead>
          <tbody>
            {DAYS.map((day) => (
              <tr key={day.index}>
                <td className="py-0.5 pr-2">{day.label}</td>
                <td className="py-0.5 pr-2">
                  <input type="checkbox" {...register(`opening_hours.${day.index}.closed`)} />
                </td>
                <td className="py-0.5 pr-2">
                  <input
                    type="time"
                    {...register(`opening_hours.${day.index}.open_time`)}
                    className="h-8 rounded border border-input px-1"
                  />
                </td>
                <td className="py-0.5">
                  <input
                    type="time"
                    {...register(`opening_hours.${day.index}.close_time`)}
                    className="h-8 rounded border border-input px-1"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <button
        type="submit"
        disabled={pending}
        className="mt-2 h-10 w-fit rounded-md bg-primary px-4 font-semibold text-primary-foreground disabled:opacity-50"
      >
        {pending ? "Saving..." : submitLabel}
      </button>
    </form>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      {children}
      {error && <span className="text-xs text-destructive">{error}</span>}
    </label>
  );
}
