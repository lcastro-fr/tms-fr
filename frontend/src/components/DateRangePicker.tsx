import dayjs from "dayjs";
import { DatePickerInput, type DatePickerInputProps } from "@mantine/dates";

import { rangoUltimoMes } from "../lib/date";

type Props = Omit<DatePickerInputProps<"range">, "type" | "presets">;

export const DateRangePicker = ({ ...props }: Props) => {
    const today = dayjs();

    return (
        <DatePickerInput
            type="range"
            presets={[
                {
                    value: [
                        today.subtract(1, "week").format("YYYY-MM-DD"),
                        today.format("YYYY-MM-DD"),
                    ],
                    label: "Últimos 7 días",
                },
                { value: rangoUltimoMes(), label: "Últimos 30 días" },
                {
                    value: [
                        today
                            .subtract(1, "month")
                            .startOf("month")
                            .format("YYYY-MM-DD"),
                        today
                            .subtract(1, "month")
                            .endOf("month")
                            .format("YYYY-MM-DD"),
                    ],
                    label: "Último mes",
                },
            ]}
            {...props}
        />
    );
};
