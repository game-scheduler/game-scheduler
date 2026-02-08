// Copyright 2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { useState } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
  FormHelperText,
  Chip,
  TextField,
  Button,
} from '@mui/material';

export interface ReminderSelectorProps {
  value: number[];
  onChange: (minutes: number[]) => void;
  error?: boolean;
  helperText?: string;
}

const PRESET_OPTIONS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
];

const MIN_MINUTES = 1;
const MAX_MINUTES = 10080;

export function ReminderSelector({ value, onChange, error, helperText }: ReminderSelectorProps) {
  const [showCustom, setShowCustom] = useState(false);
  const [customMinutes, setCustomMinutes] = useState('');

  const safeValue = Array.isArray(value) ? value : [];

  const handlePresetAdd = (event: { target: { value: string | number } }) => {
    const selectedValue = event.target.value;

    if (selectedValue === 'custom') {
      setShowCustom(true);
      return;
    }

    const presetValue =
      typeof selectedValue === 'number' ? selectedValue : parseInt(selectedValue, 10);
    if (!safeValue.includes(presetValue)) {
      onChange([...safeValue, presetValue].sort((a, b) => a - b));
    }
  };

  const handleDelete = (minuteValue: number) => {
    onChange(safeValue.filter((v) => v !== minuteValue));
  };

  const handleCustomAdd = () => {
    const num = parseInt(customMinutes, 10);
    if (
      !isNaN(num) &&
      num >= MIN_MINUTES &&
      num <= MAX_MINUTES &&
      !safeValue.includes(num) &&
      Number.isInteger(parseFloat(customMinutes))
    ) {
      onChange([...safeValue, num].sort((a, b) => a - b));
      setCustomMinutes('');
      setShowCustom(false);
    }
  };

  const handleCancel = () => {
    setCustomMinutes('');
    setShowCustom(false);
  };

  const getPresetLabel = (val: number) => {
    const preset = PRESET_OPTIONS.find((p) => p.value === val);
    return preset ? preset.label : `${val} minutes`;
  };

  return (
    <Box>
      <FormControl fullWidth error={error}>
        <InputLabel id="reminder-selector-label">Add Reminder Time</InputLabel>
        <Select
          labelId="reminder-selector-label"
          value=""
          onChange={handlePresetAdd}
          label="Add Reminder Time"
          displayEmpty={false}
        >
          {PRESET_OPTIONS.map((preset) => (
            <MenuItem
              key={preset.value}
              value={preset.value}
              disabled={safeValue.includes(preset.value)}
            >
              {preset.label}
            </MenuItem>
          ))}
          <MenuItem value="custom">Custom...</MenuItem>
        </Select>
      </FormControl>

      {showCustom && (
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <TextField
            label="Custom Minutes"
            type="number"
            value={customMinutes}
            onChange={(e) => setCustomMinutes(e.target.value)}
            inputProps={{ min: MIN_MINUTES, max: MAX_MINUTES }}
            size="small"
            sx={{ flex: 1 }}
            error={error}
          />
          <Button onClick={handleCustomAdd} variant="contained" size="small">
            Add
          </Button>
          <Button onClick={handleCancel} size="small">
            Cancel
          </Button>
        </Box>
      )}

      {safeValue.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          {safeValue.map((val) => (
            <Chip
              key={val}
              label={getPresetLabel(val)}
              onDelete={() => handleDelete(val)}
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
      )}

      {helperText && (
        <FormHelperText error={error} sx={{ mt: 1 }}>
          {helperText}
        </FormHelperText>
      )}
    </Box>
  );
}
